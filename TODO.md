# todo

- [ ] add monitor API (/health-check) route that checks load, disk space etc. and return data as JSON, so external services can ping it for health check
- [ ] allow users to set mediawiki default language from a hardcoded allow-list of common languages + czech and slovak
- [ ] allow users to hide "powered by MediaWiki" footer (`unset( $wgFooterIcons['poweredby'] );`)
- [ ] allow users to change parent domain ("unlink") without donating via dropdown selection
- [ ] on signup, determine parent domain based on app type: no-cost.site for wordpress, no-cost.forum for flarum, no-cost.wiki for mediawiki, add site_type: parent_domain hardcoded map
- [ ] send thank-you email to donors
- [ ] change CNAME linking: point to cname.<main domain> instead of <tag>.no-cost.site

---

- [ ] split tenant access logs by site_id
- [ ] logrotate on api logs (and friends)
- [ ] add backend tests (unit + integration), run after deploy to ensure we can provision sample instances and remove them etc.
- [ ] handle edge case: site is deleted and later recreated with the same tag - overwrite? rotate (append .1, .2)?
- [ ] add sync files functionality to upgrade_site cmd (to link missing/unlink removed hardlinks, etc.), just in case the apps change their file structure
- [ ] add no-cost.site footer to all apps, remove if donated
- [ ] add more mediawiki modules
- [ ] monitoring via API + BetterStack
