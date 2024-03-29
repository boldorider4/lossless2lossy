import os
import re
import literals

class Cuefile:
    def __init__(self, config):
        self.cuefile = None
        self.mode = None
        self.config = config
        self.args = config.args

    def select_cuefile(self):
        args = self.args
        if args.cover is not None:
            args.cover = os.path.realpath(os.path.expanduser(args.cover))
            if not (os.stat(args.cover) or not os.path.isfile(args.cover)):
                print('warning: cover file does not exist or is not a valid file')
                args.cover = None

        cwd = os.getcwd()
        if args.cuefile is not None:
            args.cuefile = os.path.realpath(os.path.expanduser(args.cuefile))
            if os.stat(args.cuefile) and os.path.isfile(args.cuefile):
                self.cuefile = args.cuefile
                self.mode = 0
                self._detect_cuefile_encoding()
            else:
                print('selected cuefile does not exist')
                exit(-1)
        else:
            print('guessing cufile to use...')
            candidates = [f for f in os.listdir(cwd) if f.endswith('.cue')]
            if len(candidates) == 1:
                cuefile = os.path.join(cwd, candidates[0])
                print('found cuefile {}'.format(cuefile))
                self.cuefile = cuefile
                self.mode = 0
                self._detect_cuefile_encoding()
            elif len(candidates) > 1:
                print('ambiguous cuefiles...')
                exit(-1)
            else:
                print('no cuefile present in dir...trying file by file mode...')
                self.cuefile = None
                self.mode = 1

    def extract_single_lossless_file(self):
        cuefile = self.cuefile
        config = self.config
        if not config.single_lossless_file:
            return None
        lossless_file = None

        with open(cuefile, encoding=config.cuefile_encoding) as cuefile_fd:
            for cuefile_line in cuefile_fd.readlines():
                lossless_file_match = re.match(r'^ *\t*FILE *\t*"(.*)" *(WAVE)?(FLAC)?(APE)? *\t*$', cuefile_line,
                                               re.IGNORECASE)
                if lossless_file_match is not None:
                    if lossless_file is not None:
                        return None
                    else:
                        lossless_file = os.path.join(os.path.dirname(cuefile), lossless_file_match.group(1))

    def _detect_cuefile_encoding(self):
        cuefile = self.cuefile
        encoding = literals.utf_8
        cuefile_fd = open(cuefile, 'r', encoding=literals.utf_8)
        try:
            cuefile_fd.readlines()
            cuefile_fd.close()
        except UnicodeDecodeError:
            cuefile_fd.close()
            cuefile_fd = open(cuefile, 'r', encoding=literals.cp1252)
            cuefile_fd.readlines()
            cuefile_fd.close()
            encoding = literals.cp1252
        self.config.cuefile_encoding = encoding
