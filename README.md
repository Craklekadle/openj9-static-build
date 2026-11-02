# openj9-static-build

Builds Eclipse OpenJ9 with the OpenJDK 21 class library as an interpreter-only VM in static
libraries, from the build scripts of
[oneechan-runtime](https://github.com/leros1337/oneechan-runtime) (MPL-2.0) at a pinned commit.
Those scripts fetch OpenJ9, OMR and the OpenJDK class library from their official repositories.

Releases carry the jlinked `java.home`, the static libraries with their link flags, and the
licence texts of every component in `licenses/`.

## Licences

- Eclipse OpenJ9 and Eclipse OMR: Apache-2.0 (also EPL-2.0)
- OpenJDK 21 class library and native libraries: GPLv2 with the Classpath Exception
- oneechan-runtime build scripts: MPL-2.0
- bundled in OpenJ9: libffi (MIT), zlib (Zlib)
