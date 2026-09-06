# Vendored browser dependencies

- `three.min.js`: Three.js `0.160.1`, copied from the official npm package.
- SHA-256: `170c6789f43217c96b3170f4b42fafe135de7f7cd48497a4218f9757ee1d49fa`
- SRI SHA-384: `sha384-qOkzR5Ke/XkQxuGVJ9hpFEpDlcoLtWwVYhnJf06cLIZa2vaIptSqaubivErzmD5O`
- License: MIT, preserved in `three.LICENSE.txt`.

The npm tarball was verified against the registry-published integrity value for
`three@0.160.1`. `.gitattributes` pins this JavaScript file to LF so the browser
SRI value and provenance hash remain byte-identical across Windows and POSIX
checkouts.

The local asset is the primary source for the dashboard WebGL field. Pinned
jsDelivr and unpkg URLs are retained only as availability fallbacks.
