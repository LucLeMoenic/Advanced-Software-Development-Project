FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build

WORKDIR /src
COPY AgenticLoop.csproj .
RUN dotnet restore

COPY Program.cs AgenticLoopApplication.cs ./
RUN dotnet publish --no-restore --configuration Release --output /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime

WORKDIR /app
COPY --from=build /app/publish .
COPY prompts ./prompts

USER $APP_UID

EXPOSE 8080

ENTRYPOINT ["dotnet", "/app/AgenticLoop.dll"]
CMD ["serve"]
