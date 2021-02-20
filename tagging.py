import re

class Tagging:
    def __init__(self):
        pass

    def get_album_tags_from_cuefile(self, config):
        cuefile = self.cuefile
        tag_dict = dict()
        encoding = config.cuefile_encoding

        cueprint_cmd = config.other_tools['cueprint_bin'].copy()
        cueprint_cmd.append(cuefile)
        cue_info_subprocess = subprocess_popen(cueprint_cmd)
        cue_info_subprocess.wait()
        cue_info = cue_info_subprocess.stdout

        n_track = None
        album = None
        global_artist = None
        global_genre = None
        year = None

        for line in cue_info.readlines():
            decoded_line = fix_coding_issue(line, encoding)

            n_tracks_match = re.match(r'^ *\t*no. of tracks: *\t*([0-9]+) *$', decoded_line, re.IGNORECASE)
            if n_tracks_match is not None and n_track is None:
                n_track = int(n_tracks_match.group(1))
                continue

            if config.args.performer is None:
                artist_match = re.match(r'^ *\t*performer: *\t*(.*) *$', decoded_line, re.IGNORECASE)
                if artist_match is not None and global_artist is None:
                    global_artist = artist_match.group(1)
                    continue

            if config.args.album is None:
                album_match = re.match(r'^ *\t*title: *\t*(.*) *$', decoded_line, re.IGNORECASE)
                if album_match is not None and album is None:
                    album = album_match.group(1)
                    continue
            else:
                album = config.args.album

            if config.args.genre is None:
                genre_match = re.match(r'^ *\t*genre: *\t*(.*) *$', decoded_line, re.IGNORECASE)
                if genre_match is not None and global_genre is None:
                    global_genre = genre_match.group(1)
                    continue

        if n_track is None:
            return tag_dict

        if config.args.year is None:
            with open(cuefile, encoding=encoding) as cuefile_fd:
                for cuefile_line in cuefile_fd.readlines():
                    year_match = re.match(r'^ *\t*(REM )?DATE *\t*"?([0-9]*)"? *$', cuefile_line, re.IGNORECASE)
                    if year_match is not None:
                        year = year_match.group(2)
                        break
        else:
            year = config.args.year

        track_idx = range(1, n_track+1)

        # detecting multiple lossless files
        lossless_files = dict()
        idx = 0
        with open(cuefile) as cuefile_fd:
            for cuefile_line in cuefile_fd.readlines():
                file_match = re.match(r'^ *\t*FILE *\t*"(.*)" *(WAVE)?(FLAC)?(APE)? *\t*$', cuefile_line, re.IGNORECASE)
                if file_match is not None:
                    lossless_files[track_idx[idx]] = file_match.group(1)
                    idx += 1
        if len(lossless_files) == 0:
            print('malformed cuefile: no lossless file specified')
            exit(-1)
        elif len(lossless_files) > 1:
            config.single_lossless_file = False
        else:
            config.single_lossless_file = True

        for track in track_idx:
            cueprint_cmd = config.other_tools['cueprint_bin'].copy()
            cueprint_cmd.append(cuefile)
            cueprint_cmd.append('-n')
            cueprint_cmd.append(str(track))
            cue_info_subprocess = subprocess_popen(cueprint_cmd)
            cue_info_subprocess.wait()
            cue_info = cue_info_subprocess.stdout

            artist = None
            title = None
            genre = None
            for line in cue_info.readlines():
                decoded_line = fix_coding_issue(line, encoding)

                # 'perfomer' is a mispelling due to a bug in cueprint
                if config.args.performer is None:
                    artist_match = re.match(r'^ *\t*perfomer: *\t*(.*) *$', decoded_line, re.IGNORECASE)
                    if artist_match is not None:
                        artist = artist_match.group(1)
                        if artist == '':
                            artist = global_artist
                        continue
                else:
                    artist = config.args.performer

                title_match = re.match(r'^ *\t*title: *\t*(.*) *$', decoded_line, re.IGNORECASE)
                if title_match is not None:
                    title = title_match.group(1)
                    continue

                if config.args.genre is None:
                    genre_match = re.match(r'^ *\t*genre: *\t*(.*) *$', decoded_line, re.IGNORECASE)
                    if genre_match is not None:
                        genre = genre_match.group(1)
                        if genre == '':
                            genre = global_genre
                        continue
                else:
                    genre = config.args.genre

            track_tag_dict = dict()
            track_tag_dict['artist'] = artist.title()
            track_tag_dict['album'] = album.title()
            track_tag_dict['year'] = year
            track_tag_dict['title'] = title.title()
            track_tag_dict['genre'] = genre.title()
            track_tag_dict['comment'] = 'Generated by all new lossless2lossy.py!'
            track_tag_dict['disctotal'] = '1'
            if config.single_lossless_file:
                track_tag_dict['infile'] = f'split-track{track:02d}.wav'
            else:
                lossless_file = lossless_files[track]
                track_tag_dict['losslessfile'] = lossless_file
                filename, ext = os.path.splitext(lossless_file)
                track_tag_dict['infile'] = filename + '.wav'
            track_tag_dict['outfile'] = f'{track:02d} {slugify(title)}.m4a'
            if 1 not in tag_dict:
                tag_dict[1] = dict()
            tag_dict[1][track] = track_tag_dict

        return tag_dict

    def get_album_tags_from_dir(self, config):
        cwd = os.getcwd()
        audio_source_files = [f for f in os.listdir(cwd) if f.endswith('.ape')
                              or f.endswith('.wv')
                              or f.endswith('.flac')]
        tag_dict = dict()

        decode_stderr = list()
        for track_file in audio_source_files:

            if config.decoder == 'ffmpeg_bin':
                decode_cmd = config.other_tools[config.decoder].copy()
                decode_cmd.append('-i')
                decode_cmd.append(track_file)
                decode_cmd.append('-y')
                decode_cmd.append('-f')
                decode_cmd.append('ffmetadata')

                decode_subprocess = subprocess_popen(decode_cmd)
                decode_subprocess.wait()
                decode_stderr.append(decode_subprocess.stderr)
            else:
                raise NotImplementedError()

        track_idx = 0
        for track_file in audio_source_files:
            artist = None
            album = None
            year = None
            disc = None
            disctotal = None
            title = None
            genre = None
            track = None
            filename, ext = os.path.splitext(track_file)
            converted_filename = filename + '.wav'

            if config.decoder == 'ffmpeg_bin':
                decode_output = decode_stderr[track_idx]
                for line in decode_output.readlines():
                    decoded_line = line.decode(config.cuefile_encoding)

                    if config.args.performer is None:
                        artist_match = re.match(r'^ +ARTIST +: +(.*)$', decoded_line, re.IGNORECASE)
                        if artist_match is not None:
                            artist = artist_match.group(1)
                            continue
                    else:
                        artist = config.args.performer

                    if config.args.album is None:
                        album_match = re.match(r'^ +ALBUM +: +(.*)$', decoded_line, re.IGNORECASE)
                        if album_match is not None:
                            album = album_match.group(1)
                            continue
                    else:
                        album = config.args.album

                    if config.args.year is None:
                        year_match = re.match(r' +DATE +: +([0-9][0-9][0-9][0-9]).?[0-9]?.?[0-9]?', decoded_line,
                                              re.IGNORECASE)
                        if year_match is not None:
                            year = int(year_match.group(1))
                            continue
                    else:
                        year = config.args.year

                    disc_match = re.match(r'^ +disc +: +([0-9]+)$', decoded_line, re.IGNORECASE)
                    if disc_match is not None:
                        disc = int(disc_match.group(1))
                        continue

                    disctotal_match = re.match(r'^ +DISCTOTAL +: +([0-9]+)$', decoded_line,
                                               re.IGNORECASE)
                    if disctotal_match is not None:
                        disctotal = int(disctotal_match.group(1))
                        continue

                    title_match = re.match(r'^ +title +: +(.*)$', decoded_line, re.IGNORECASE)
                    if title_match is not None:
                        title = title_match.group(1)
                        continue

                    if config.args.genre is None:
                        genre_match = re.match(r'^ +GENRE +: +(.*)$', decoded_line, re.IGNORECASE)
                        if genre_match is not None:
                            genre = genre_match.group(1)
                            continue
                    else:
                        genre = config.args.genre

                    track_match = re.match(r'^ +track +: +(.*)$', decoded_line, re.IGNORECASE)
                    if track_match is not None:
                        track = int(track_match.group(1))
                        continue
            else:
                raise NotImplementedError()

            track_tag_dict = dict()
            track_tag_dict['artist'] = artist.title()
            track_tag_dict['album'] = album.title()
            track_tag_dict['year'] = year
            track_tag_dict['title'] = title.title()
            track_tag_dict['genre'] = genre.title()
            track_tag_dict['comment'] = 'Generated by all new lossless2lossy.py!'
            # disctotal is unused from now because infered by the size of the tag_dict dict
            track_tag_dict['disctotal'] = disctotal
            track_tag_dict['losslessfile'] = track_file
            track_tag_dict['infile'] = converted_filename
            track_tag_dict['outfile'] = f'{track:02d} {slugify(title)}.m4a'
            if disc not in tag_dict:
                tag_dict[disc] = dict()
            tag_dict[disc][track] = track_tag_dict
            track_idx += 1

        config.single_lossless_file = False

        return tag_dict
