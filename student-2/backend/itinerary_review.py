import json
import os
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated, Literal

import anyio
import httpx
from pydantic import BaseModel, ConfigDict, Field, RootModel, ValidationError, model_validator

from ai_clients import IntegrationError, validate_overview, validate_summary


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ToolPlan(StrictModel):
    tools: list[Literal["itinerary.get_itinerary", "itinerary.get_overview"]] = Field(min_length=1, max_length=2)


class ReviewStop(StrictModel):
    id: int = Field(gt=0)
    day: int = Field(ge=1, le=31)
    activity: str = Field(min_length=1, max_length=160)
    notes: str = Field(max_length=1000)
    sortOrder: int = Field(default=0, ge=0)


class Finding(StrictModel):
    day: int = Field(ge=1, le=31)
    observation: str = Field(min_length=1, max_length=500)
    suggestion: str = Field(max_length=500)
    stopIds: list[int] = Field(max_length=200)
    weatherDates: list[str] = Field(max_length=1)


class Review(StrictModel):
    findings: list[Finding] = Field(max_length=5)
    limitation: str = Field(max_length=600)


class EditOperation(StrictModel):
    action: Literal["move_day", "swap_days", "move_stop", "reorder_before", "reorder_after", "undo", "add_stop", "remove_stop", "update_stop", "shift_dates"]
    sourceDay: int = Field(ge=1, le=31)
    targetDay: int = Field(ge=1, le=31)
    stopId: int = Field(ge=0)
    targetStopId: int = Field(default=0, ge=0)
    activity: str | None = Field(default=None, min_length=1, max_length=160)
    notes: str | None = Field(default=None, max_length=1000)
    startDate: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class EditSelection(StrictModel):
    operation: EditOperation | None
    clarification: str = Field(max_length=500)


class AssistantOperation(EditOperation):
    action: Literal["move_day", "swap_days", "move_stop", "add_stop", "remove_stop", "update_stop", "shift_dates", "undo"]


class AssistantSelection(EditSelection):
    operation: AssistantOperation | None


class DayAction(StrictModel):
    action: Literal["move_day", "swap_days"]
    sourceDay: int = Field(ge=1, le=31)
    targetDay: int = Field(ge=1, le=31)


class MoveAction(StrictModel):
    action: Literal["move_stop"]
    stopId: int = Field(gt=0)
    targetDay: int = Field(ge=1, le=31)


class AddAction(StrictModel):
    action: Literal["add_stop"]
    day: int = Field(ge=1, le=31)
    activity: str = Field(min_length=1, max_length=160)
    notes: str = Field(max_length=1000, description="Only notes explicitly requested by the user; otherwise empty string.")


class RemoveAction(StrictModel):
    action: Literal["remove_stop"]
    stopId: int = Field(gt=0)


class UpdateAction(StrictModel):
    action: Literal["update_stop"]
    stopId: int = Field(gt=0)
    field: Literal["activity", "notes"]
    value: str = Field(max_length=1000, description="Exact replacement text from the user's request.")


class DateAction(StrictModel):
    action: Literal["shift_dates"]
    startDate: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class UndoAction(StrictModel):
    action: Literal["undo"]


class ClarifyAction(StrictModel):
    action: Literal["clarify"]
    message: str = Field(min_length=1, max_length=500)


class ModelEdit(RootModel[Annotated[DayAction | MoveAction | AddAction | RemoveAction | UpdateAction | DateAction | UndoAction | ClarifyAction, Field(discriminator="action")]]):
    def selection(self, itinerary, question):
        choice = self.root
        if isinstance(choice, ClarifyAction):
            return {"operation": None, "clarification": choice.message}
        request_text = " ".join(question.split()).casefold()
        if isinstance(choice, AddAction):
            activity = " ".join(choice.activity.split()).casefold()
            notes = " ".join(choice.notes.split()).casefold()
            if (not activity or activity not in request_text or (notes and notes not in request_text)
                    or not re.search(rf"\bday\s+0*{choice.day}\b", question, re.IGNORECASE)):
                return {"operation": None, "clarification": "Name the activity and its day number, including any notes you want added."}
        if isinstance(choice, UpdateAction) and choice.value and " ".join(choice.value.split()).casefold() not in request_text:
            return {"operation": None, "clarification": "What exact replacement title or notes should I use?"}
        operation = {"action": choice.action, "sourceDay": 1, "targetDay": 1, "stopId": 0}
        if isinstance(choice, DayAction):
            operation.update(sourceDay=choice.sourceDay, targetDay=choice.targetDay)
        elif isinstance(choice, AddAction):
            operation.update(sourceDay=choice.day, targetDay=choice.day, activity=choice.activity, notes=choice.notes)
        elif isinstance(choice, DateAction):
            operation["startDate"] = choice.startDate
        elif isinstance(choice, (MoveAction, RemoveAction, UpdateAction)):
            stop = next((stop for stop in itinerary["stops"] if stop["id"] == choice.stopId), None)
            if stop is None:
                raise ValueError("Unknown selected stop")
            operation.update(stopId=choice.stopId, sourceDay=stop["day"], targetDay=stop["day"])
            if isinstance(choice, MoveAction):
                operation["targetDay"] = choice.targetDay
            elif isinstance(choice, UpdateAction):
                operation[choice.field] = choice.value
        return {"operation": operation, "clarification": ""}


class EditChange(StrictModel):
    id: int = Field(gt=0)
    activity: str = Field(min_length=1, max_length=160)
    notes: str = Field(max_length=1000)
    fromDay: int = Field(ge=1, le=31)
    toDay: int = Field(ge=1, le=31)
    fromOrder: int = Field(ge=0)
    toOrder: int = Field(ge=0)


class ProposedStop(ReviewStop):
    id: int = Field(ge=0)


class DetailChange(StrictModel):
    kind: Literal["add_stop", "remove_stop", "update_stop"]
    id: int = Field(ge=0)
    before: ReviewStop | None
    after: ProposedStop | None

    @model_validator(mode="after")
    def valid_states(self):
        if ((self.before is None) != (self.kind == "add_stop")
                or (self.after is None) != (self.kind == "remove_stop")
                or any(stop.id != self.id or not stop.activity.strip() for stop in (self.before, self.after) if stop is not None)):
            raise ValueError("Invalid edit states")
        if self.kind == "update_stop" and ((self.before.day, self.before.sortOrder) != (self.after.day, self.after.sortOrder)
                                           or self.before.model_dump() == self.after.model_dump()):
            raise ValueError("Invalid detail update")
        return self


class DateChange(StrictModel):
    kind: Literal["shift_dates"]
    fromStartDate: str
    fromEndDate: str
    toStartDate: str
    toEndDate: str

    @model_validator(mode="after")
    def valid_dates(self):
        values = [self.fromStartDate, self.fromEndDate, self.toStartDate, self.toEndDate]
        start, end, target_start, target_end = [date.fromisoformat(value) for value in values]
        if (any(parsed.isoformat() != value for parsed, value in zip((start, end, target_start, target_end), values))
                or not 0 <= (end - start).days <= 30 or end - start != target_end - target_start or start == target_start):
            raise ValueError("Invalid date shift")
        return self


class EditPreview(StrictModel):
    tripId: int = Field(gt=0)
    token: str = Field(min_length=1, max_length=4096)
    changes: list[EditChange | DetailChange | DateChange] = Field(min_length=1, max_length=200)
    expiresIn: Literal[600]


class AppliedEdit(StrictModel):
    tripId: int = Field(gt=0)
    applied: Literal[True]
    changes: list[EditChange | DetailChange | DateChange] = Field(min_length=1, max_length=200)


def expected_detail_change(operation, itinerary):
    if operation.targetStopId != 0 or operation.sourceDay != operation.targetDay:
        raise ValueError("Unexpected stop selection")
    if operation.action == "shift_dates":
        if (operation.sourceDay, operation.stopId) != (1, 0) or operation.startDate is None:
            raise ValueError("Invalid date selection")
        start = date.fromisoformat(operation.startDate)
        end = start + timedelta(days=itinerary["summary"]["dayCount"] - 1)
        return DateChange(kind="shift_dates", fromStartDate=itinerary["summary"]["startDate"],
                          fromEndDate=itinerary["summary"]["endDate"], toStartDate=operation.startDate,
                          toEndDate=end.isoformat()).model_dump()
    before = next((stop for stop in itinerary["stops"] if stop["id"] == operation.stopId and stop["day"] == operation.sourceDay), None)
    if operation.action == "add_stop":
        if operation.stopId != 0 or len(itinerary["stops"]) >= 200 or operation.activity is None:
            raise ValueError("Invalid new stop")
        after = {"id": 0, "day": operation.targetDay, "activity": operation.activity.strip(), "notes": operation.notes or "",
                 "sortOrder": max((stop["sortOrder"] for stop in itinerary["stops"] if stop["day"] == operation.targetDay), default=-1) + 1}
    else:
        if before is None:
            raise ValueError("Unknown stop")
        after = None if operation.action == "remove_stop" else {
            **before, **{field: getattr(operation, field) for field in ("activity", "notes") if getattr(operation, field) is not None}}
        if after is not None:
            after["activity"] = after["activity"].strip()
    return DetailChange(kind=operation.action, id=operation.stopId, before=before, after=after).model_dump()


def validate_undo_changes(preview, itinerary):
    current = {stop["id"]: stop for stop in itinerary["stops"]}
    identifiers = []
    dates = 0
    for change in preview.changes:
        if isinstance(change, DateChange):
            dates += 1
            if (change.fromStartDate, change.fromEndDate) != (itinerary["summary"]["startDate"], itinerary["summary"]["endDate"]):
                raise ValueError("Trip dates changed during preview")
            continue
        identifiers.append(change.id)
        stop = current.get(change.id)
        if isinstance(change, DetailChange):
            if change.kind == "add_stop":
                if stop is not None or change.id == 0:
                    raise ValueError("Invalid restored stop")
            elif stop != change.before.model_dump():
                raise ValueError("Trip changed during preview")
            if change.after and change.after.day > itinerary["summary"]["dayCount"]:
                raise ValueError("Invalid target day")
        elif (stop is None or (change.fromDay, change.fromOrder, change.activity, change.notes) !=
              (stop["day"], stop["sortOrder"], stop["activity"], stop["notes"]) or change.toDay > itinerary["summary"]["dayCount"]):
            raise ValueError("Invalid undo position")
    if len(identifiers) != len(set(identifiers)) or dates > 1 or (dates and identifiers):
        raise ValueError("Invalid undo result")


class ItineraryEditor:
    def __init__(self, mcp, model):
        self.mcp, self.model = mcp, model

    def preview_operation(self, trip_id, operation):
        try:
            operation = EditOperation.model_validate(operation)
        except ValidationError:
            raise IntegrationError("invalid_edit") from None
        if operation.action not in ("reorder_before", "reorder_after", "undo"):
            raise IntegrationError("invalid_edit")
        return self.preview(trip_id, operation=operation.model_dump())

    def preview(self, trip_id, question=None, operation=None):
        explicit = operation is not None
        validated = False
        try:
            itinerary = validate_itinerary(self.mcp.itinerary(trip_id), trip_id)
            selection = EditSelection(operation=EditOperation.model_validate(operation), clarification="") if explicit else AssistantSelection.model_validate(self.model.generate("select_edit", {
                "question": question, "itinerary": itinerary,
            }, AssistantSelection.model_json_schema()))
            operation = selection.operation
            if operation is None:
                if not selection.clarification.strip():
                    raise ValueError("Missing clarification")
                return {"tripId": trip_id, "clarification": selection.clarification, "preview": None}
            day_count = itinerary["summary"]["dayCount"]
            if selection.clarification or max(operation.sourceDay, operation.targetDay) > day_count:
                raise ValueError("Invalid operation")
            allowed = {"add_stop": {"activity", "notes"}, "update_stop": {"activity", "notes"}, "shift_dates": {"startDate"}}.get(operation.action, set())
            if any(getattr(operation, field) is not None for field in {"activity", "notes", "startDate"} - allowed):
                raise ValueError("Unexpected edit details")
            expected_orders = None
            expected_detail = None
            if operation.action == "undo":
                if (operation.sourceDay, operation.targetDay, operation.stopId, operation.targetStopId) != (1, 1, 0, 0):
                    raise ValueError("Invalid undo selection")
                selected = itinerary["stops"]
            elif operation.action in ("add_stop", "remove_stop", "update_stop", "shift_dates"):
                expected_detail = expected_detail_change(operation, itinerary)
                selected = itinerary["stops"]
            elif operation.action in ("reorder_before", "reorder_after"):
                if operation.sourceDay != operation.targetDay or operation.stopId == operation.targetStopId:
                    raise ValueError("Invalid reorder selection")
                ordered = [stop for stop in itinerary["stops"] if stop["day"] == operation.sourceDay]
                identifiers = [stop["id"] for stop in ordered]
                if operation.stopId not in identifiers or operation.targetStopId not in identifiers:
                    raise ValueError("Unknown reorder stop")
                moving = next(stop for stop in ordered if stop["id"] == operation.stopId)
                ordered.remove(moving)
                anchor = next(index for index, stop in enumerate(ordered) if stop["id"] == operation.targetStopId)
                ordered.insert(anchor + (operation.action == "reorder_after"), moving)
                if [stop["id"] for stop in ordered] == identifiers:
                    raise IntegrationError("edit_no_change")
                expected_orders = {stop["id"]: index for index, stop in enumerate(ordered)}
                selected = [stop for stop in ordered if stop["id"] in expected_orders]
            else:
                if (operation.sourceDay == operation.targetDay or operation.targetStopId != 0
                        or (operation.action != "move_stop" and operation.stopId != 0)):
                    raise ValueError("Invalid move selection")
                selected = [stop for stop in itinerary["stops"] if stop["day"] == operation.sourceDay
                            and (operation.action != "move_stop" or stop["id"] == operation.stopId)]
                if operation.action == "swap_days":
                    selected += [stop for stop in itinerary["stops"] if stop["day"] == operation.targetDay]
            if not selected and operation.action not in ("undo", "add_stop", "shift_dates"):
                raise ValueError("No matching stops")
            validated = True
            try:
                preview = EditPreview.model_validate(self.mcp.preview_edit(trip_id, operation.model_dump(exclude_defaults=True)))
            except IntegrationError as exception:
                if operation.action == "undo" and exception.code == "invalid_edit":
                    raise IntegrationError("undo_unavailable") from None
                raise
            if preview.tripId != trip_id:
                raise ValueError("Wrong trip")
            if operation.action == "undo":
                validate_undo_changes(preview, itinerary)
                return {"tripId": trip_id, "clarification": "", "preview": preview.model_dump(), "tool": "itinerary.preview_edit"}
            if expected_detail is not None:
                if [change.model_dump() for change in preview.changes] != [expected_detail]:
                    raise ValueError("Unexpected edit result")
                return {"tripId": trip_id, "clarification": "", "preview": preview.model_dump(), "tool": "itinerary.preview_edit"}
            if any(not isinstance(change, EditChange) for change in preview.changes):
                raise ValueError("Unexpected edit result")
            changed_ids = {change.id for change in preview.changes}
            selected_ids = {stop["id"] for stop in selected}
            if (preview.tripId != trip_id or len(changed_ids) != len(preview.changes)
                    or not changed_ids <= selected_ids
                    or (operation.action != "undo" and changed_ids != selected_ids)):
                raise ValueError("Invalid preview")
            for change in preview.changes:
                stop = next(stop for stop in selected if stop["id"] == change.id)
                if (change.fromDay, change.fromOrder, change.activity, change.notes) != (stop["day"], stop["sortOrder"], stop["activity"], stop["notes"]):
                    raise ValueError("Trip changed during preview")
                if not 1 <= change.toDay <= day_count:
                    raise ValueError("Invalid target day")
                if operation.action != "undo":
                    target = operation.targetDay if stop["day"] == operation.sourceDay else operation.sourceDay
                    if change.toDay != target or (expected_orders is not None and change.toOrder != expected_orders[change.id]):
                        raise ValueError("Unexpected edit result")
            return {"tripId": trip_id, "clarification": "", "preview": preview.model_dump(), "tool": "itinerary.preview_edit"}
        except (ValidationError, ValueError, TypeError, KeyError, OverflowError):
            raise IntegrationError("invalid_edit" if explicit and not validated else "invalid_dependency_response") from None

    def apply(self, trip_id, token):
        try:
            result = AppliedEdit.model_validate(self.mcp.apply_edit(trip_id, token))
            if result.tripId != trip_id:
                raise ValueError("Wrong trip")
            return {**result.model_dump(), "tool": "itinerary.apply_edit"}
        except (ValidationError, ValueError, TypeError, KeyError):
            raise IntegrationError("invalid_dependency_response") from None


def validate_itinerary(body, trip_id):
    try:
        if not isinstance(body, dict) or set(body) != {"summary", "stops"}:
            raise ValueError("Invalid itinerary")
        summary = validate_summary(body["summary"], trip_id)
        if not isinstance(body["stops"], list) or len(body["stops"]) > 200:
            raise ValueError("Invalid stops")
        stops = [ReviewStop.model_validate(stop).model_dump() for stop in body["stops"]]
        planned = {stop["day"] for stop in stops}
        if (len(stops) != summary["stopCount"] or len({stop["id"] for stop in stops}) != len(stops)
                or any(day > summary["dayCount"] for day in planned)
                or summary["unplannedDays"] != [day for day in range(1, summary["dayCount"] + 1) if day not in planned]):
            raise ValueError("Inconsistent itinerary")
        return {"summary": summary, "stops": sorted(stops, key=lambda stop: (stop["day"], stop["sortOrder"], stop["id"]))}
    except (ValidationError, ValueError, TypeError, KeyError):
        raise IntegrationError("invalid_dependency_response") from None


class ReviewModel:
    def __init__(self, url, model):
        self.url = url.rstrip("/")
        self.model = model
        configured = os.getenv("ITINERARY_REVIEW_PROMPT")
        self.prompt_path = Path(configured) if configured else (
            Path(__file__).resolve().parent.parent.parent / "ai-services/agentic-loop/prompts/itinerary-review-v1.txt")
        self.edit_prompt_path = Path(os.getenv("ITINERARY_EDIT_PROMPT", str(self.prompt_path.with_name("itinerary-edit-v1.txt"))))

    def generate(self, stage, data, schema):
        return anyio.run(self._generate, stage, data, schema)

    async def _generate(self, stage, data, schema):
        try:
            prompt_path = self.edit_prompt_path if stage == "select_edit" else self.prompt_path
            instructions = prompt_path.read_text(encoding="utf-8")
            with anyio.fail_after(20):
                async with httpx.AsyncClient(timeout=20) as client:
                    prompt_data = {"itinerary": data.get("itinerary"), "question": data.get("question")} if stage == "select_edit" else data
                    payload = {"model": self.model, "system": instructions,
                               "prompt": json.dumps({"stage": stage, "data": prompt_data}), "stream": False,
                               "format": ModelEdit.model_json_schema() if stage == "select_edit" else schema,
                               "options": {"temperature": 0, "num_predict": 1600}, "keep_alive": "30m"}
                    async with client.stream("POST", f"{self.url}/api/generate", json=payload) as response:
                        if response.status_code != 200:
                            raise IntegrationError("dependency_unavailable")
                        content = bytearray()
                        async for chunk in response.aiter_bytes(chunk_size=4096):
                            if len(content) + len(chunk) > 32768:
                                raise IntegrationError("invalid_dependency_response")
                            content.extend(chunk)
                        body = json.loads(content)
                        if not isinstance(body, dict) or body.get("done") is not True:
                            raise ValueError("Incomplete generation")
                        result = json.loads(body["response"])
                        return ModelEdit.model_validate(result).selection(data["itinerary"], data.get("question", "")) if stage == "select_edit" else result
        except IntegrationError:
            raise
        except (TimeoutError, httpx.TimeoutException):
            raise IntegrationError("dependency_timeout") from None
        except (httpx.HTTPError, OSError):
            raise IntegrationError("dependency_unavailable") from None
        except (ValueError, TypeError, KeyError):
            raise IntegrationError("invalid_dependency_response") from None


class ItineraryReviewer:
    def __init__(self, mcp, model):
        self.mcp = mcp
        self.model = model

    def review(self, trip_id, question):
        try:
            plan = ToolPlan.model_validate(self.model.generate("select_tools", {"question": question}, ToolPlan.model_json_schema()))
            if plan.tools not in (["itinerary.get_itinerary"], ["itinerary.get_itinerary", "itinerary.get_overview"]):
                raise ValueError("Invalid tool sequence")
            itinerary = validate_itinerary(self.mcp.itinerary(trip_id), trip_id)
            results = {"itinerary.get_itinerary": itinerary}
            weather = None
            if "itinerary.get_overview" in plan.tools:
                overview = validate_overview(self.mcp.overview(trip_id), trip_id)
                if overview["summary"] != itinerary["summary"]:
                    raise ValueError("Trip changed during review")
                weather = overview["weather"]
                results["itinerary.get_overview"] = overview
            review = Review.model_validate(self.model.generate("review", {
                "question": question, "toolResults": results,
            }, Review.model_json_schema()))
            if not review.findings and not review.limitation.strip():
                raise ValueError("Empty review")
            findings = []
            for finding in review.findings:
                if finding.day > itinerary["summary"]["dayCount"] or not finding.observation.strip():
                    raise ValueError("Invalid finding day")
                day_stops = [stop for stop in itinerary["stops"] if stop["day"] == finding.day]
                identifiers = {stop["id"] for stop in day_stops}
                forecast_date = (date.fromisoformat(itinerary["summary"]["startDate"]) + timedelta(days=finding.day - 1)).isoformat()
                forecasts = [day for day in (weather or {}).get("days", []) if day["date"] == forecast_date]
                if (len(set(finding.stopIds)) != len(finding.stopIds) or not set(finding.stopIds).issubset(identifiers)
                        or (finding.weatherDates and (finding.weatherDates != [forecast_date] or not forecasts))):
                    raise ValueError("Unsupported evidence reference")
                findings.append({**finding.model_dump(), "evidence": {
                    "stopCount": len(day_stops), "stops": [stop for stop in day_stops if stop["id"] in finding.stopIds],
                    "weather": forecasts if finding.weatherDates else [],
                }})
            return {"tripId": trip_id, "tools": plan.tools, "findings": findings,
                    "limitation": review.limitation, "weather": weather}
        except (ValidationError, ValueError, TypeError, KeyError):
            raise IntegrationError("invalid_dependency_response") from None