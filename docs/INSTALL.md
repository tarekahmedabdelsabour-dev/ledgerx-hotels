# Install

```
cd ~/frappe-bench-v16/apps
git clone <repo-url> ledgerx_hotels
cd ~/frappe-bench-v16
echo "" >> sites/apps.txt && echo "ledgerx_hotels" >> sites/apps.txt   # skip if bench get-app is used
./env/bin/pip install -e apps/ledgerx_hotels
ln -sfn ~/frappe-bench-v16/apps/ledgerx_hotels/ledgerx_hotels/public sites/assets/ledgerx_hotels
bench --site mysite.localhost install-app ledgerx_hotels
bench --site mysite.localhost migrate && bench --site mysite.localhost clear-cache
```
Then restart the server.

## First setup (Hotels workspace)
1. **Hotel Settings:** company, tax rates, and the accounts for service charge, VAT and tourism fee, plus room and services revenue accounts.
2. **Currency Exchange:** add rates between every currency you accept and the company currency.
3. **Hotel Payment Method:** one per currency and way of paying (for example Cash EGP, Cash USD, Card EUR), each with its own cash/bank account in that currency.
4. **Hotel, Room Type, Hotel Room**, then **Rate Plan** (nothing can be priced without a plan covering every night), then optional **Promotions** and **Service Items**.
5. Roles are created automatically: Hotel Manager, Hotel Front Desk, Hotel Housekeeping, Hotel Accountant.

## Known limits
- The guest's receivable account must be in the company currency (the normal case).
- Deposits are applied to an invoice from the same customer's unallocated payments; a company that pays deposits for future bookings may see them applied to an earlier invoice.
- Rooms, not room types, are what gets reserved: confirming assigns a specific room.
