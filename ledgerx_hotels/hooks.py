app_name = "ledgerx_hotels"
app_title = "Hotels"
app_publisher = "LedgerX"
app_description = "Hotel management: rooms, reservations without double booking, season rates and promotions, multi-currency guest folios and accounting links"
app_email = "hello@ledgerx.local"
app_license = "mit"

required_apps = ["erpnext", "ledgerx"]

add_to_apps_screen = [
	{
		"name": "ledgerx_hotels",
		"logo": "/assets/ledgerx_hotels/images/hotels.svg",
		"title": "Hotels",
		"route": "/desk/hotels",
		"has_permission": "ledgerx_hotels.install.check_app_permission",
	}
]

scheduler_events = {
	"cron": {
		"0 5 * * *": ["ledgerx_hotels.tasks.bill_corporate_daily"],
		"30 6 * * *": ["ledgerx_hotels.tasks.daily_cleaning"],
	},
}

after_install = "ledgerx_hotels.install.after_install"
after_migrate = "ledgerx_hotels.install.after_migrate"
