# todo

- [ ] split tenant access logs by site_id
- [ ] logrotate on api logs (and friends)
- [ ] add backend tests (unit + integration), run after deploy to ensure we can provision sample instances and remove them etc.
- [ ] handle edge case: site is deleted and later recreated with the same tag - overwrite? rotate (append .1, .2)?
- [ ] add sync files functionality to upgrade_site cmd (to link missing/unlink removed hardlinks, etc.), just in case the apps change their file structure
- [ ] add no-cost.site footer to all apps, remove if donated
- [ ] add more mediawiki modules
- [ ] monitoring via API + BetterStack
