#!/usr/bin/env python3
"""OpenJ9 linked into a program's image, when that image is a library a host program opened.

App containers run an app by turning its executable into a library and opening it with dlopen. The
VM's code is then in an image whose Mach-O type is MH_DYLIB, not MH_EXECUTE, and two checks made for
"linked into the executable" stop working:

- runtime/j9vm/jvm.c (getj9bin / preloadLibrary): only an MH_EXECUTE image counted as the VM
  linked in. Any other image was taken for a real libjvm.dylib, and the VM looked for its other
  libraries (libomrsig.dylib, libj9vm29.dylib...) as files next to it, found none and stopped. Now
  an image that is not libjvm.dylib, given -Djava.home (the embedder's option), counts as linked in
  too; the VM's entry points are looked up in that image (in the executable, as before, through
  RTLD_DEFAULT).
- src/java.base/unix/native/libjava/jni_util_md.c (getProcessHandle): the JDK looks for its
  statically linked JNI libraries (JNI_OnLoad_net, ...) in the main executable only
  (dlopen(NULL, RTLD_FIRST)), which is the host program's. It now looks in the image that holds the
  JDK's code when that image is not the executable.

Run after apply-openj9-patches.sh:  python3 loaded-image.py <folder of the openj9-jdk21 tree>
"""
import sys
from pathlib import Path

src = Path(sys.argv[1])


def edit(path, pairs):
    text = path.read_text()
    if "LOADED_IMAGE_PATCH" in text:
        print(f"{path}: already patched")
        return
    for old, new in pairs:
        if text.count(old) != 1:
            sys.exit(f"{path}: expected one occurrence of:\n{old}")
        text = text.replace(old, new)
    path.write_text(text)
    print(f"{path}: patched")


edit(src / "openj9/runtime/j9vm/jvm.c", [
    (
        "static BOOLEAN vmLinkedIntoExecutable = FALSE;\n",
        "static BOOLEAN vmLinkedIntoExecutable = FALSE;\n"
        "/* LOADED_IMAGE_PATCH: the image the VM is linked into when it is a library a host program\n"
        " * opened (an app run by an app container), else NULL (the executable). */\n"
        "static char *vmLinkedIntoLibrary = NULL;\n"
        "\n"
        "static BOOLEAN\n"
        "isLibjvmPath(const char *path)\n"
        "{\n"
        "\tconst char *base = strrchr(path, '/');\n"
        "\tbase = (NULL == base) ? path : (base + 1);\n"
        "\treturn (0 == strncmp(base, \"libjvm.\", 7)) ? TRUE : FALSE;\n"
        "}\n",
    ),
    (
        "\tif ((NULL != libraryInfo.dli_fbase) && (MH_EXECUTE == ((const struct mach_header *)libraryInfo.dli_fbase)->filetype)) {\n"
        "\t\tvmLinkedIntoExecutable = TRUE;\n",
        "\tif ((NULL != libraryInfo.dli_fbase) && (MH_EXECUTE != ((const struct mach_header *)libraryInfo.dli_fbase)->filetype)\n"
        "\t\t&& (NULL != staticJavaHome) && (NULL != libraryInfo.dli_fname) && !isLibjvmPath(libraryInfo.dli_fname)\n"
        "\t) {\n"
        "\t\t/* Linked into a program that a host program opened as a library: the same as linked into\n"
        "\t\t * the executable, the entry points being looked up in that image. */\n"
        "\t\tfree(vmLinkedIntoLibrary);\n"
        "\t\tvmLinkedIntoLibrary = strdup(libraryInfo.dli_fname);\n"
        "\t}\n"
        "\tif ((NULL != libraryInfo.dli_fbase)\n"
        "\t\t&& ((MH_EXECUTE == ((const struct mach_header *)libraryInfo.dli_fbase)->filetype) || (NULL != vmLinkedIntoLibrary))\n"
        "\t) {\n"
        "\t\tvmLinkedIntoExecutable = TRUE;\n",
    ),
    (
        "\t\t/* The library is part of the executable: look its entry points up there. */\n"
        "\t\tfree(buffer);\n"
        "\t\treturn RTLD_DEFAULT;\n",
        "\t\t/* The library is part of the executable: look its entry points up there. */\n"
        "\t\tfree(buffer);\n"
        "\t\tif (NULL != vmLinkedIntoLibrary) {\n"
        "\t\t\t/* ...or in the program's image, opened as a library by its host. */\n"
        "\t\t\tvoid *image = dlopen(vmLinkedIntoLibrary, RTLD_LAZY | RTLD_NOLOAD);\n"
        "\t\t\tif (NULL != image) {\n"
        "\t\t\t\treturn image;\n"
        "\t\t\t}\n"
        "\t\t}\n"
        "\t\treturn RTLD_DEFAULT;\n",
    ),
])

edit(src / "src/java.base/unix/native/libjava/jni_util_md.c", [
    (
        "#ifdef __APPLE__\n"
        "    procHandle = (void*)dlopen(NULL, RTLD_FIRST);\n",
        "#ifdef __APPLE__\n"
        "    /* LOADED_IMAGE_PATCH: the JDK linked into a program that a host program opened as a\n"
        "     * library (an app run by an app container): its built-in libraries are in that image. */\n"
        "    {\n"
        "        Dl_info info;\n"
        "        if (dladdr((void *)getProcessHandle, &info) != 0 && info.dli_fbase != NULL\n"
        "                && ((const struct mach_header *)info.dli_fbase)->filetype != MH_EXECUTE\n"
        "                && info.dli_fname != NULL) {\n"
        "            procHandle = dlopen(info.dli_fname, RTLD_LAZY | RTLD_NOLOAD | RTLD_FIRST);\n"
        "            if (procHandle != NULL) {\n"
        "                return procHandle;\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "    procHandle = (void*)dlopen(NULL, RTLD_FIRST);\n",
    ),
    (
        "#include \"dlfcn.h\"\n",
        "#include \"dlfcn.h\"\n"
        "#ifdef __APPLE__\n"
        "#include <mach-o/loader.h>\n"
        "#endif\n",
    ),
])
