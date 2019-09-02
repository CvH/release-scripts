#!/usr/bin/env python

import hashlib
import json
import os
import re

class ChunkedHash():
    # Calculate hash for chunked data
    @staticmethod
    def hash_bytestr_iter(bytesiter, hasher, ashexstr=True):
        for block in bytesiter:
            hasher.update(block)
        return (hasher.hexdigest() if ashexstr else hasher.digest())

    # Read file in blocks/chunks to be memory efficient
    @staticmethod
    def file_as_blockiter(afile, blocksize=65536):
        with afile:
          block = afile.read(blocksize)
          while len(block) > 0:
              yield block
              block = afile.read(blocksize)

    # Calculate sha256 hash for a file
    @staticmethod
    def calculate_sha256(fname):
        try:
            return ChunkedHash.hash_bytestr_iter(ChunkedHash.file_as_blockiter(open(fname, "rb")), hashlib.sha256())
        except:
            raise
            return ""

class ReleaseFile():
    def __init__(self, path, url):
        self._path = path
        self._url = url
        self._output_file = 'releases.json'

        self.display_name = {'Generic.x86_64': 'Generic AMD/Intel/NVIDIA (x86_64)',
                             'imx6.arm': 'Cubox-i2/i4 and Hummingboard (iMX6)',
                             'KVIM.arm': 'Khadas Vim',
                             'KVIM2.arm': 'Khadas Vim 2',
                             'LePotato.arm': 'LePotato (AML-S905X-CC)',
                             'MiQi.arm': 'Rockchip MiQi RK3328',
                             'Odroid_C2.aarch64': 'Odroid C2',
                             'Odroid_C2.arm': 'Odroid C2',
                             'RK3328.arm': 'Rockchip RK3328',
                             'RK3399.arm': 'Rockchip RK3399',
                             'RPi.arm': 'Raspberry Pi Zero and 1',
                             'RPi2.arm': 'Raspberry Pi 2 and 3',
                             'S805.arm': 'Amlogic S805',
                             'S905.aarch64': 'Amlogic S905',
                             'S905.arm': 'Amlogic S905',
                             'S912.arm': 'Amlogic S912',
                             'Slice.arm': 'Slice (CM1)',
                             'Slice3.arm': 'Slice (CM3)',
                             'TinkerBoard.arm': 'Asus TinkerBoard',
                             'Virtual.x86_64': 'Virtual x86_64',
                             'WeTek_Core.arm': 'WeTek Core',
                             'WeTek_Hub.aarch64': 'WeTek Hub',
                             'WeTek_Hub.arm': 'WeTek Hub',
                             'WeTek_Play.arm': 'WeTek Play',
                             'WeTek_Play_2.aarch64': 'WeTek Play 2',
                             'WeTek_Play_2.arm': 'WeTek Play 2',
                            }

        self.update_json = {}

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass

    def UpdateAll(self):
        outfile = os.path.join(self._path, self._output_file)

        self.ReadFile(outfile)

        self.UpdateFile(self._path, self._url)

        self.WriteFile(outfile)

    def UpdateCombinedFile(self):
        outfile = os.path.join(self._path, self._output_file)

        self.ReadFile(outfile)

        for (dirpath, dirnames, filenames) in os.walk(self._path):
            for project in dirnames:
                self.UpdateFile(os.path.join(self._path, project), "%s%s/" % (self._url, project))
            break

        self.WriteFile(outfile)

    def UpdateProjectFile(self, project):
        path = os.path.join(self._path, project)
        url = "%s%s/" % (self._url, project)
        outfile = os.path.join(path, self._output_file)

        self.ReadFile(outfile)

        self.UpdateFile(path, url)

        self.WriteFile(outfile)

    def UpdateFile(self, path, url):
        if not os.path.exists(path):
            raise Exception("ERROR: %s is not a valid path" % path)

        files = []
        for (dirpath, dirnames, filenames) in os.walk(path):
            files.extend(filenames)
            break

        trains = []
        for release in files:
            # x.x.x
            regex = re.compile(r'([0-9]+)\.[0-9]\.[0-9]+')
            if regex.search(release):
                trains.append(regex.findall(release)[0])
            # x.90.x
            regex = re.compile(r'([0-9]+)\.90\.[0-9]+')
            if regex.search(release):
                trains.append(str(int(regex.findall(release)[0]) + 1))
            # x.95.x
            regex = re.compile(r'([0-9]+)\.95\.[0-9]+')
            if regex.search(release):
                trains.append(str(int(regex.findall(release)[0]) + 1))

        trains = list(set(trains))

        for i,train in enumerate(trains):
            trains[i] = 'LibreELEC-' + train + '.0'

        print(trains)

        builds = []
        for release in files:
            regex = re.compile(r'LibreELEC-(.*)-[0-9]')
            if regex.match(release):
                builds.append(regex.findall(release)[0])
        builds = list(set(builds))

        print(builds)

        for train in trains:
            self.update_json[train] = {'url': url}
            self.update_json[train]['prettyname_regex'] = '^LibreELEC-.*-([0-9]+\.[0-9]+\.[0-9]+)'
            self.update_json[train]['project'] = {}
            major_version = re.findall(r'([0-9]+).[0-9]', train)
            for build in builds:
                self.update_json[train]['project'][build] = {'releases': {}}
                self.update_json[train]['project'][build]['displayName'] = self.display_name[build]
                releases = [x for x in files if (re.search(major_version[0] + '+.[0-9].[0-9]+', x) or
                                                 re.search(str(int(major_version[0]) - 1) + '+.90.[0-9]+', x) or
                                                 re.search(str(int(major_version[0]) - 1) + '+.95.[0-9]+', x)) and
                                                 re.search(build, x) and
                                                 re.search('.tar', x) and not
                                                 re.search('noobs', x)]
                for i,release in enumerate(sorted(releases)):
                    key = "%s;%s;%s" % (train, build, release)
                    if key not in self.oldhash:
                        print("Adding: %s" % release)
                        file_digest = ChunkedHash().calculate_sha256(os.path.join(path, release))
                        file_size = str(os.path.getsize(os.path.join(path, release)))
                    else:
                        file_digest = self.oldhash[key]["sha256"]
                        file_size = self.oldhash[key]["size"]

                    # .tar
                    self.update_json[train]['project'][build]['releases'][i] = {'file': {'name': release}}
                    self.update_json[train]['project'][build]['releases'][i]['file']['sha256'] = file_digest
                    self.update_json[train]['project'][build]['releases'][i]['file']['size'] = file_size

                    # .img.gz
                    image = [x for x in files if re.match(release.strip('.tar') + '.img.gz', x)]
                    try:
                        key = "%s;%s;%s" % (train, build, image[0])
                        if key not in self.oldhash:
                            print("Adding: %s" % image[0])
                            file_digest = ChunkedHash().calculate_sha256(os.path.join(path, image[0]))
                            file_size = str(os.path.getsize(os.path.join(path, image[0])))
                        else:
                            file_digest = self.oldhash[key]["sha256"]
                            file_size = self.oldhash[key]["size"]
                        self.update_json[train]['project'][build]['releases'][i]['image'] = {'name': image[0]}
                        self.update_json[train]['project'][build]['releases'][i]['image']['sha256'] = file_digest
                        self.update_json[train]['project'][build]['releases'][i]['image']['size'] = file_size
                    except IndexError:
                        self.update_json[train]['project'][build]['releases'][i]['image'] = {'name': ''}
                        self.update_json[train]['project'][build]['releases'][i]['image']['sha256'] = ''
                        self.update_json[train]['project'][build]['releases'][i]['image']['size'] = ''

    # Read old file if it exists, to avoid recalculating hashes when possible
    def ReadFile(self, input_file):
        self.oldhash = {}
        if os.path.exists(input_file):
            try:
                with open(input_file, 'r') as f:
                    oldjson = json.loads(f.read())
                    for train in oldjson:
                        for build in oldjson[train]['project']:
                            for release in oldjson[train]['project'][build]['releases']:
                                r = oldjson[train]['project'][build]['releases'][release]["file"]
                                self.oldhash["%s;%s;%s" % (train, build, r["name"])] = {"sha256": r["sha256"], "size": r["size"]}
                                try:
                                    i = oldjson[train]['project'][build]['releases'][release]["image"]
                                    self.oldhash["%s;%s;%s" % (train, build, i["name"])] = {"sha256": i["sha256"], "size": i["size"]}
                                except:
                                    pass
            except:
                self.oldhash = {}

    def WriteFile(self, output_file):
        with open(output_file, 'w') as f:
            f.write(json.dumps(self.update_json))

'''
if len(sys.argv) < 2:
    print("ERROR: Need to know which project - RPi, RPi2, Generic etc.")
    sys.exit(1)
'''

with ReleaseFile('/var/www/releases.libreelec.tv/', 'http://releases.libreelec.tv/') as rf:
    rf.UpdateAll()
