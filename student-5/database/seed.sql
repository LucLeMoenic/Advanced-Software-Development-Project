-- Student 5 - Travel Logistics & Advisory Service
-- Sample data, written from the perspective of an Australian passport holder.
--
-- This script is only executed when the destinations table is empty, so the
-- explicit ids below are safe and keep the foreign keys readable.
--
-- The advisory text is illustrative sample data for the assignment. Real visa
-- and border rules change frequently and must always be checked against
-- Smartraveller and the destination government before travelling.

INSERT INTO destinations (id, country, visa_requirement, notes) VALUES
    (1,  'Japan',          'visa-free',        'Short-stay tourist entry for Australian passport holders. Visit Japan Web pre-registration speeds up immigration and customs.'),
    (2,  'Indonesia',      'visa-on-arrival',  'Visa on arrival is issued at major airports including Bali (DPS). Passport must have at least six months validity remaining.'),
    (3,  'Vietnam',        'eVisa',            'Single and multiple entry eVisa applied for online before departure. Carry a printed copy of the approval letter.'),
    (4,  'United States',  'eVisa',            'ESTA electronic travel authorisation under the Visa Waiver Program. Apply at least 72 hours before the first flight.'),
    (5,  'France',         'visa-free',        'Schengen short-stay rules apply - 90 days in any rolling 180 day period, counted across all Schengen countries.'),
    (6,  'India',          'eVisa',            'Tourist eVisa applied for online. Entry is limited to designated airports and seaports listed on the approval.'),
    (7,  'New Zealand',    'visa-free',        'An NZeTA request and the International Visitor Levy must be completed before travel, even though no visa is required.'),
    (8,  'Thailand',       'visa-free',        'Short-stay tourist entry. Proof of onward travel and accommodation is sometimes checked at immigration.'),
    (9,  'China',          'embassy-visa',     'Tourist (L) visa lodged in person at a visa application centre. Requires a full itinerary and confirmed accommodation.'),
    (10, 'Brazil',         'eVisa',            'Electronic visitor visa required for Australian passport holders. Processing can take several weeks in peak season.'),
    (11, 'United Kingdom', 'visa-free',        'Short-stay visitor entry. An Electronic Travel Authorisation is being phased in, so confirm status before booking.'),
    (12, 'Fiji',           'visa-free',        'Visitor permit granted on arrival for short stays. A return or onward ticket must be presented at the border.');

INSERT INTO weather_notes (destination_id, season, notes) VALUES
    (1,  'Spring (Mar-May)',   'Mild days and heavy cherry blossom crowds. Pack layers because inland evenings stay cold well into April.'),
    (1,  'Summer (Jun-Aug)',   'Hot and humid with the tsuyu rains through June, and typhoon disruption building from late August.'),
    (2,  'Wet (Nov-Mar)',      'Daily afternoon downpours and high humidity in Bali. Island ferry services are frequently cancelled.'),
    (2,  'Dry (Apr-Oct)',      'Best diving visibility and reliable sunshine. Book accommodation early for the July to August peak.'),
    (3,  'Winter (Dec-Feb)',   'Cool and drizzly in Hanoi and the north while the south stays hot and dry - pack for both climates.'),
    (4,  'Winter (Dec-Feb)',   'Snow and ice regularly delay connecting flights through northern hubs such as Chicago and New York.'),
    (5,  'Summer (Jun-Aug)',   'Warm to hot with periodic heatwaves. Many regional businesses close for the August holiday period.'),
    (5,  'Winter (Dec-Feb)',   'Cold with short daylight hours in Paris. Alpine routes require snow chains or winter tyres.'),
    (6,  'Monsoon (Jun-Sep)',  'Heavy monsoon rain causes flooding and road closures, particularly along the west coast and in Mumbai.'),
    (7,  'Winter (Jun-Aug)',   'South Island alpine passes can close at short notice. Carry chains and check road conditions each morning.'),
    (8,  'Hot (Mar-May)',      'Extreme heat and seasonal haze inland. Schedule sightseeing for early morning or late afternoon.'),
    (9,  'Autumn (Sep-Nov)',   'Clear and comfortable nationwide, but the early October national holiday week is extremely busy.'),
    (10, 'Summer (Dec-Feb)',   'Hot and humid with heavy afternoon storms in Rio. Carnival accommodation sells out months ahead.'),
    (11, 'Autumn (Sep-Nov)',   'Wet and windy with early sunsets. Allow extra connection time for rail disruption after storms.');

INSERT INTO transit_options (destination_id, type, details) VALUES
    (1,  'rail',         'A Japan Rail Pass covers most Shinkansen services between major cities and is cheapest bought before arrival.'),
    (1,  'metro',        'Tokyo Metro and Toei lines accept Suica or Pasmo IC cards, which also work on buses and in convenience stores.'),
    (2,  'rideshare',    'Grab and Gojek are widely used in Jakarta and Bali, with designated rideshare pickup zones at the airports.'),
    (2,  'ferry',        'Fast boats link Bali to the Gili Islands and Nusa Penida, but sailings are cancelled in rough weather.'),
    (3,  'rail',         'The Reunification Express runs Hanoi to Ho Chi Minh City. Book soft sleeper berths several days ahead.'),
    (4,  'airport-link', 'The JFK AirTrain connects all terminals to the subway and Long Island Rail Road at Jamaica and Howard Beach.'),
    (4,  'rideshare',    'Uber and Lyft pickups at major US airports are restricted to signed rideshare levels rather than the kerbside.'),
    (5,  'rail',         'TGV high speed services link Paris to Lyon and Marseille, and seat reservations are compulsory on every train.'),
    (5,  'metro',        'A Paris Navigo Easy card can be loaded with single Metro tickets and passed between travellers who are not both riding.'),
    (6,  'metro',        'The Delhi Metro is air conditioned and cashless via smart card, with separate security queues for women.'),
    (7,  'bus',          'InterCity coaches reach most towns, but the Cook Strait crossing between islands is a separate ferry booking.'),
    (8,  'ferry',        'Chao Phraya express boats are the fastest way to reach riverside temples in Bangkok during traffic peaks.'),
    (9,  'rail',         'High speed G-trains require your passport at booking and at the station gate, so allow 30 minutes for security.'),
    (11, 'airport-link', 'The Heathrow Express reaches London Paddington in about 15 minutes, while the Elizabeth line is slower but cheaper.');
