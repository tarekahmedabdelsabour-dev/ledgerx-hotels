# Hotels (ledgerx_hotels)

Hotel management for LedgerX, built on the accounting, selling and CRM modules. Installed as its own app; nothing in the core is modified.

## What it does
- **Rooms:** hotels, room types, rooms with housekeeping status (Clean, Dirty, Maintenance, Out of Order).
- **Reservations without double booking:** confirming a reservation takes every night of the stay for one room (`Room Night Lock`, one unique row per room and night), so two people can never hold the same room for the same night, even at the same moment.
- **Rates and offers:** season rate plans per room type, meal plan (room only, bed & breakfast, half, full board), public / corporate / agent prices (for one named company or for all), weekend increase, minimum nights, promotion codes (percent or amount, validity, usage limit). A stay that crosses a season change is priced night by night.
- **Multi-currency:** the guest bill has one currency; the guest can pay in any accepted currency (Hotel Payment Method = currency + cash/bank account). Each payment line becomes a Payment Entry at that day's rate (or a rate typed at the desk).
- **Folio and accounting:** the guest folio gathers room nights, meals and services; service charge, VAT and tourism fee are computed from the settings; check-out creates a Sales Invoice in the folio currency, applying earlier deposits as advances. Company or agent bookings can stay open and be invoiced together monthly.
- **Cancellation policy:** free until N days before arrival, then a percentage of the first night; no-show charges the first night.
- **Links:** guests are Customers (so the CRM sees them); airport pick-up can name a Vehicle; reports for arrivals/departures, occupancy and open folios.

## Install
See `docs/INSTALL.md`.

## Tests
`python3 ledgerx_hotels/tests/test_logic.py` runs the pure rules (season pricing, promotions, taxes, currency maths, cancellation) with no site.
Everything that touches the database (locks, folios, Payment Entries, invoices) must be tried on a test site first.
