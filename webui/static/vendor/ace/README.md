# Ace editor assets

Pinned from `ajaxorg/ace-builds` tag `v1.40.0`, directory
`src-min-noconflict/`:

- `ace.js`
- `mode-c_cpp.js`
- `mode-verilog.js`
- `theme-tomorrow_night_eighties.js`

These files are served locally so the Web UI editor works without a CDN or an
extra frontend build. Workers are disabled because this application uses Ace
for editing and syntax colouring, not language-server diagnostics.

Ace is distributed under the BSD license included in `LICENSE`.
