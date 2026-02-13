# todo

- [ ] handle edge case: site is deleted and later recreated with the same tag - overwrite? rotate (append .1, .2)?
- [ ] settings
  - [ ] per service type settings (e.g. Mediawiki: set default skin, upload favicon) - investigate (by default, it requires writing to config, is there maybe a module to write this info to DB and inject it to let admins change default config via MW UI?)
  - [x] custom domain linking
    - [x] link_domain command
  - [ ] fixup (migrate site, cache flush, sync files)
    - [ ] add sync files functionality to upgrade_site cmd (to link missing/unlink removed hardlinks, etc.), just in case the apps change their file structure
  - [x] data export
  - [x] account deletion
- [x] backups!!!!!
- [ ] monitoring!!
