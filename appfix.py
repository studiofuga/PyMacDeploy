#! /usr/bin/env python
import argparse
import os
import subprocess
import sys
import shutil
import re


""" A file structure, with name and destination path.
"""
class File:
    def __init__(self, name, destination):
        self._name = name
        self._dest = destination

    @property
    def name(self):
        return self._name

    @property
    def destination(self):
        return self._dest


class Fixer:

    def __init__(self, app):
        self.bundle = app
        self.list = list()
        self.verbose = False
        if not os.path.exists(app):
            raise RuntimeError("File {} not found.".format(app))
        self.pathfilter = ["/usr/lib/", "/System/"]

    def setVerbose(self, verbose=True):
        self.verbose = verbose

    def _getDependencies_impl(self, path):
        o = subprocess.Popen(['/usr/bin/otool', '-L', path], stdout=subprocess.PIPE)

        for line in o.stdout:
            l = line.decode()

            if l[0] == '\t':
                depname = l.split(' ', 1)[0][1:]

                if not re.search("@(executable_path|loader_path|rpath)", depname):
                    yield depname

    def _getDependencies(self, path):
        return list(self._getDependencies_impl(path))

    def _checkIfFiltered(self, path):
        for i in self.pathfilter:
            if i in path:
                return True
        return False

    def addAllFilesInBundle(self):
        macospath = os.path.join(self.bundle, "Contents", "MacOS");
        files = [File(f,os.path.join("MacOS", f)) for f in os.listdir(macospath) if os.path.isfile(os.path.join(macospath, f))]
        self.list.extend(files)
        frameworkspath = os.path.join(self.bundle, "Contents", "Frameworks")
        files = [File(f,os.path.join("Frameworks",f)) for f in os.listdir(frameworkspath) if os.path.isfile(os.path.join(macospath, f))]
        self.list.extend(files)

    def fix(self):
        already_processed = set()
        for file in self.list:

            if file in already_processed:
                if self.verbose:
                    print("W {} already processed, skipping.".format(file))
                continue

            if self.verbose:
                print(". Processing file: {}".format(file.name))

            fullfilepath = os.path.join(self.bundle, "Contents", file.destination)
            if not os.path.exists(fullfilepath):
                if self.verbose:
                    print(". File doesn't exist: copy {} to {}".format(file.name, fullfilepath))

                shutil.copy(file.name, fullfilepath)

            dependencies = self._getDependencies(fullfilepath)
            if self.verbose:
                print(". Dependencies for {}:\n\t{}".format(file.name, "\n\t".join(dependencies)))

            filtered_dependencies = [x for x in dependencies if not self._checkIfFiltered(x) and not x == fullfilepath]

            if self.verbose:
                print(". Filtered Dependencies for {}:\n\t{}".format(file.name, "\n\t".join(filtered_dependencies)))

            newfiles = [File(x,x) for x in filtered_dependencies]
            self.list.extend(newfiles)

            already_processed.add(fullfilepath)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("appbundle", help="The path of the Application Bundle (.app)")
    parser.add_argument("-s", "--scan", help="Scan current bundle for Executable and Frameworks (under MacOS and Frameworks paths)", action="store_true")
    parser.add_argument("-v", "--verbose", help="Turn verbosity on", action="store_true")
    parser.add_argument("-q", "--quiet", help="Turn verbosity off", action="store_true")
    args = parser.parse_args()

    fixer = Fixer(args.appbundle)

    if args.scan:
        fixer.addAllFilesInBundle()

    if args.verbose:
        fixer.setVerbose(True)

    if args.quiet:
        fixer.setVerbose(False)

    fixer.fix()
