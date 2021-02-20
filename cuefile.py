import os

class Cuefile:
    def __init__(self, cuefile):
        self.cuefile = cuefile
        self.mode = None

    def select_cuefile(self, args):
        args.cover = os.path.abspath(args.cover)
        if args.cover is None or not (os.stat(args.cover) or os.path.isfile(args.cover)):
            print('warning: cover file does not exist or is not a valid file')
            args.cover = None

        cwd = os.getcwd()
        cuefile = args.cuefile
        if cuefile is not None:
            cuefile = os.path.abspath(args.cuefile)
            if os.stat(cuefile) and os.path.isfile(cuefile):
                self.cuefile = cuefile
                self.mode = 0
                return (0, cuefile)
            else:
                print('selected cuefile does not exist')
                self.cuefile = None
                self.mode = -1
                return (-1, '')
        else:
            print('guessing cufile to use...')
            candidates = [f for f in os.listdir(cwd) if f.endswith('.cue')]
            if len(candidates) == 1:
                cuefile = os.path.join(cwd, candidates[0])
                print('found cuefile {}'.format(cuefile))
                self.cuefile = cuefile
                self.mode = 0
                return (0, cuefile)
            elif len(candidates) > 1:
                print('ambiguous cuefiles...')
                self.cuefile = None
                self.mode = -1
                return (-1, '')
            else:
                print('no cuefile present in dir')
                self.cuefile = None
                self.mode = 1
                return (1, '')

    def _detect_cuefile_encoding(self):
        cuefile = self.cuefile
        encoding = 'utf-8'
        cuefile_fd = open(cuefile, 'r', encoding='utf-8')
        try:
            cuefile_fd.readlines()
            cuefile_fd.close()
        except UnicodeDecodeError:
            cuefile_fd.close()
            cuefile_fd = open(cuefile, 'r', encoding='cp1252')
            cuefile_fd.readlines()
            cuefile_fd.close()
            encoding = 'cp1252'
        return encoding

    def extract_single_lossless_file(self, config):
        cuefile = self.cuefile
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
        return lossless_file
