# Vendored asset provenance

The review page serves these JavaScript/font files from its own token-protected
origin; no asset CDN or package manager is required at runtime. Project-owned
code is MIT, but these files retain their own terms. Complete direct and bundled
notices are provided in [NOTICE](../NOTICE) and the license files below. Embedded
legal comments and all shipped binary/minified bytes are preserved.

## Matching published builds

Versions below identify npm packages, not necessarily font design versions.
Source links identify a verified matching publication, not an unrecorded original
download URL. Publisher tarball integrity metadata was checked and shipped bytes
compared to archive members; the task-list wrapper is the stated exception.

| Shipped file | Matching package/publication | Archive member | Terms |
| --- | --- | --- | --- |
| `vendor/markdown-it.min.js` | [markdown-it 14.1.0](https://registry.npmjs.org/markdown-it/14.1.0) | `dist/markdown-it.min.js` | [MIT](vendor/LICENSE.markdown-it.txt), bundled dependencies in NOTICE |
| `vendor/markdown-it-task-lists.min.js` | [markdown-it-task-lists 2.1.0](https://registry.npmjs.org/markdown-it-task-lists/2.1.0) | `dist/markdown-it-task-lists.min.js`, existing wrapper modification | [ISC](vendor/LICENSE.markdown-it-task-lists.txt) |
| `vendor/markdown-it-footnote.min.js` | [markdown-it-footnote 4.0.0](https://registry.npmjs.org/markdown-it-footnote/4.0.0) | `dist/markdown-it-footnote.min.js` | [MIT](vendor/LICENSE.markdown-it-footnote.txt) |
| `vendor/highlight.min.js` | [@highlightjs/cdn-assets 11.10.0](https://registry.npmjs.org/%40highlightjs%2Fcdn-assets/11.10.0) | `highlight.min.js` | [BSD-3-Clause](vendor/LICENSE.highlight.js.txt) |
| `vendor/mermaid.min.js` | [mermaid 11.4.1](https://registry.npmjs.org/mermaid/11.4.1) | `dist/mermaid.min.js` | [MIT](vendor/LICENSE.mermaid.txt), mixed bundled licenses in NOTICE |
| `fonts/inter-latin-var.woff2` | [@fontsource-variable/inter 5.0.20](https://registry.npmjs.org/%40fontsource-variable%2Finter/5.0.20) | `files/inter-latin-wght-normal.woff2` | [OFL-1.1](fonts/OFL-inter.txt) |
| `fonts/source-serif-4-latin-var.woff2` | [@fontsource-variable/source-serif-4 5.0.20](https://registry.npmjs.org/%40fontsource-variable%2Fsource-serif-4/5.0.20) | `files/source-serif-4-latin-wght-normal.woff2` | [OFL-1.1](fonts/OFL-source-serif-4.txt), Reserved Font Name Source |
| `fonts/jetbrains-mono-400.woff2` | [@fontsource/jetbrains-mono 5.0.20](https://registry.npmjs.org/%40fontsource%2Fjetbrains-mono/5.0.20) | `files/jetbrains-mono-latin-400-normal.woff2` | [OFL-1.1](fonts/OFL.txt) |
| `fonts/jetbrains-mono-700.woff2` | Same JetBrains publication | `files/jetbrains-mono-latin-700-normal.woff2` | [OFL-1.1](fonts/OFL.txt) |

Nerd-font names in CSS prefer fonts already installed on the user's system; no
Nerd Font binary is bundled. Fonts above are redistributed unchanged with their
names and OFL notices. Package 5.0.20 is the matching JetBrains publication;
current latest is not used as a substitute source/version claim.

The task-list file preserves its existing 22-character function/return wrapper
insertion relative to the 2.1.0 published minified build. Complete byte comparison
found only those insertions; all other code and the banner are unchanged. This is
a modified ISC distribution, not an assertion of byte-identical upstream content.
No asset was upgraded or modified during public-readiness preparation.

## Bundled attribution and version limits

Mermaid's byte-matching 11.4.1 package includes `dist/mermaid.min.js.map`. Its
source paths identify 70 package/version pairs, including repeated versions of
some dependencies. NOTICE maps those pairs to their complete published legal
texts and textual third-party notices; identical texts are deduplicated without
dropping any component mapping. Licenses include MIT, ISC, BSD-3-Clause and
Apache-2.0; DOMPurify preserves its MPL-2.0 OR Apache-2.0 dual terms. Khroma's
package license text supplies MIT even though its metadata field is absent.
Top-level Mermaid MIT does not relabel these components. Original Lodash,
Underscore and Cytoscape embedded credits remain present.

Mermaid's Jison-generated parser/lexer glue and Cytoscape's embedded MIT credits
have additional attribution in NOTICE. Jison and jQuery reference notice versions
are labeled as references, not unsupported source-map or embedded-build pins.
Jison-lex's published README/source declares MIT without a separate copyright
notice; that absence and the provided standard terms are stated explicitly.

Markdown-it's release commit `0fe7ccb4b7f30236fb05f623be6924961d296d3d`
has no dependency lock and its published browser build has no source map. Its
browser includes mdurl, uc.micro, linkify-it, punycode.js and entities; argparse is
CLI-only. The published dependency ranges and verified reference notice versions
are retained in NOTICE. Exact resolved browser dependency versions are not all
established; in particular entities 4.4.0/4.5.0 provide identical BSD-2-Clause
copyright/terms. Do not describe those references as an exact build lock.

## Shipped SHA-256

These digests cover the actual distributed bytes, including the task-list
modification. They are content checks, not a security or vulnerability assessment.

| File | SHA-256 |
| --- | --- |
| `vendor/markdown-it.min.js` | `38c70a1e7ca91ab40e2d9e6e60129851a717ed1c7d4acbbdd41bf9503791cf68` |
| `vendor/markdown-it-task-lists.min.js` | `4f3b23f41bb3787957da2602fbccc4df0d017928c1fce62583159e096b832a81` |
| `vendor/markdown-it-footnote.min.js` | `d6fee58a3b56c5742fa18f3e01f1d317cc99975683ebd39c9195cb2aff0c2e42` |
| `vendor/highlight.min.js` | `471ef9ae90c407af440fcdc48edfeeb562106b3267bd12d99071c162fb52ed32` |
| `vendor/mermaid.min.js` | `a43bc1afd446f9c4cc66ac5dd45d02e8d65e26fc5344ec0ef787f88d6ddb6f9e` |
| `fonts/inter-latin-var.woff2` | `f052ee44c3728dfd23aba8a4567150bc314d23903026fbb6ad089422c2df56af` |
| `fonts/source-serif-4-latin-var.woff2` | `42c9a2125f752f225d8aa7b1d95075c4c6a7f91e78d521a50ae318b9ab15bd04` |
| `fonts/jetbrains-mono-400.woff2` | `7c53386f55c866c1b4c9309c4bcf74eda10896aab3a1780b0af5cc4976e27a27` |
| `fonts/jetbrains-mono-700.woff2` | `ed8b8f71b22bf3b6e1ec1cf9b24dd999785aae33d6256950c1f86c97e423b6ef` |

## Updating assets

An update is a separate reviewed change: establish the actual publication/build,
verify integrity and shipped hashes, retain complete direct/bundled copyright and
license terms, consider security/support effects, and run the existing renderer
and Markdown regressions. Do not strip banners, silently alter fonts/Reserved
Font Names or infer transitive licensing from a top-level SPDX label.
