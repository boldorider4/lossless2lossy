import argparse
import subprocess
import unicodedata
import os
import re


class ConvertConfig:
    def __init__(self, args):
        self.decode_tools = dict()
        self.encode_tools = dict()
        self.other_tools = dict()
        self.decoder = ''
        self.encoder = ''
        self.splitter = ''
        self.tagger = ''
        self.cuefile_encoding = 'utf-8'
        self.args = args


def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-q', '--cuefile', type=str, help='specifies the cuefile to use for track info')
    parser.add_argument('-c', '--cover', type=str, help='specifies the cover file')
    parser.add_argument('-y', '--year', type=str, help='sets the year')
    parser.add_argument('-g', '--genre', type=str, help='sets the genre')
    parser.add_argument('-a', '--album', type=str, help='sets the album')
    parser.add_argument('-p', '--performer', type=str, help='sets the performer')
    parser.add_argument('-k', '--comment', type=str, help='sets the comment')
    parser.add_argument('-n', '--disc', type=str, help='sets the disc number')
    parser.add_argument('-m', '--discs', type=str, help='sets the total number of discs')
    parser.add_argument('-b', '--bitrate', type=str, help='sets the bitrate')
    parser.add_argument('-d', '--path', type=str, help='sets the sets the output path for the converted files')
    args = parser.parse_args()
    return args


def create_config(args):
    config = ConvertConfig(args)
    config.decode_tools = { 'flac_bin' : 'flac',
                            'shntool_bin' : ['shntool', 'split', '-o', 'wav', '-O', 'always'],
                            'ffmpeg_bin' : ['ffmpeg'],
                            'mac_bin' : 'mac',
                            'wvunpack_bin' : 'wvunpack' }
    config.encode_tools = { 'ffmpeg_bin' : ['ffmpeg'],
                            'afconvert_bin' : ['afconvert', '-v', '-d', 'aac', '-f', 'm4af', '-u', 'pgcm', '2', '-q',
                                               '127', '-s', '2', '--soundcheck-generate'] }
    config.other_tools = { 'mp4box_bin' : 'mp4box',
                           'ffmpeg_bin' : 'ffmpeg',
                           'cueprint_bin' : 'cueprint',
                           'atomicparsley_bin' : ['AtomicParsley', '--overWrite'] }
    config.decoder = 'ffmpeg_bin'
    config.encoder = 'afconvert_bin'
    config.splitter = 'shntool_bin'
    config.tagger = 'atomicparsley_bin'
    return config


def check_tools(config):
    
    # check other tools
    for tool in config.other_tools.values():
        proc = subprocess.Popen(['which',tool],stdout=subprocess.PIPE)
        if len(proc.stdout.readlines()) == 0:
            print('{} is missing and is required'.format(tool))
            return False        

    # check decode tools
    is_any_tool_installed = False
    for tool in config.decode_tools.values():
        proc = subprocess.Popen(['which',tool],stdout=subprocess.PIPE)
        is_any_tool_installed |= (len(proc.stdout.readlines()) > 0)
    if not is_any_tool_installed:
        error_msg = 'neither of '
        for tool in config.decode_tools.values():
            error_msg += tool + ' '
        error_msg += 'is installed'
        print(error_msg)
        return False

    # check encode tools
    is_any_tool_installed = False
    for tool in config.encode_tools.values():
        proc = subprocess.Popen(['which',tool],stdout=subprocess.PIPE)
        is_any_tool_installed |= (len(proc.stdout.readlines()) > 0)
    if not is_any_tool_installed:
        error_msg = 'neither of '
        for tool in config.encode_tools.values():
            error_msg += tool + ' '
        error_msg += 'are installed'
        print(error_msg)
        return False

    return True


def select_cuefile(cuefile=None):
    cwd = os.getcwd()
    if cuefile:
        if os.path.exists(os.path.join(cwd, cuefile)):
            return (0, cuefile)
        else:
            print('selected cuefile does not exist')
            return (-1, '')
    else:
        print('guessing cufile to use...')
        candidates = [f for f in os.listdir(cwd) if f.endswith('.cue')]
        if len(candidates) == 1:
            cuefile = os.path.join(cwd, candidates[0])
            print('found cuefile {}'.format(cuefile))
            return (0, cuefile)
        elif len(candidates) > 1:
            print('ambiguous cuefiles...')
            return (-1, '')
        else:
            print('no cuefile present in dir')
            return (1, '')


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


def get_album_tags_from_cuefile(cuefile, config):
    tag_dict = dict()

    cue_info = subprocess.Popen([config.other_tools['cueprint_bin'], cuefile],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

    n_track = None
    album = None
    global_artist = None
    global_genre = None
    year = None

    for line in cue_info.readlines():
        n_tracks_match = re.match(r'^ *\t*no. of tracks: *\t*([0-9]+) *$', line.decode('utf-8'), re.IGNORECASE)
        if n_tracks_match is not None and n_track is None:
            n_track = int(n_tracks_match.group(1))
            continue

        if config.args.performer is None:
            artist_match = re.match(r'^ *\t*performer: *\t*(.*) *$', line.decode('utf-8'), re.IGNORECASE)
            if artist_match is not None and global_artist is None:
                global_artist = artist_match.group(1)
                continue

        if config.args.album is None:
            album_match = re.match(r'^ *\t*title: *\t*(.*) *$', line.decode('utf-8'), re.IGNORECASE)
            if album_match is not None and album is None:
                album = album_match.group(1)
                continue
        else:
            album = config.args.album

        if config.args.genre is None:
            genre_match = re.match(r'^ *\t*genre: *\t*(.*) *$', line.decode('utf-8'), re.IGNORECASE)
            if genre_match is not None and global_genre is None:
                global_genre = genre_match.group(1)
                continue

    if n_track is None:
        return tag_dict

    if config.args.year is None:
        with open(cuefile) as cuefile_fd:
            for cuefile_line in cuefile_fd.readlines():
                year_match = re.match(r'^ *\t*(REM )?DATE *\t*([0-9]*) *$', cuefile_line, re.IGNORECASE)
                if year_match is not None:
                    year = year_match.group(2)
                    break
    else:
        year = config.args.year

    for track in range(1, n_track+1):
        cue_info = subprocess.Popen([config.other_tools['cueprint_bin'], cuefile, '-n', str(track)],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

        artist = None
        title = None
        genre = None
        lossless_file = None
        for line in cue_info.readlines():
            # 'perfomer' is a mispelling due to a bug in cueprint
            if config.args.performer is None:
                artist_match = re.match(r'^ *\t*perfomer: *\t*(.*) *$', line.decode('utf-8'), re.IGNORECASE)
                if artist_match is not None:
                    artist = artist_match.group(1)
                    if artist == '':
                        artist = global_artist
                    continue
            else:
                artist = config.args.performer

            title_match = re.match(r'^ *\t*title: *\t*(.*) *$', line.decode('utf-8'), re.IGNORECASE)
            if title_match is not None:
                title = title_match.group(1)
                continue

            if config.args.genre is None:
                genre_match = re.match(r'^ *\t*genre: *\t*(.*) *$', line.decode('utf-8'), re.IGNORECASE)
                if genre_match is not None:
                    genre = genre_match.group(1)
                    if genre == '':
                        genre = global_genre
                    continue
            else:
                genre = config.args.genre

            lossless_file_match = re.match(r'^ *\t*FILE *\t*"(.*)" *(WAVE)?(FLAC)?(APE)? *\t*$', line.decode('utf-8'), re.IGNORECASE)
            if lossless_file_match is not None:
                lossless_file = lossless_file_match.group()
                continue

        track_tag_dict = dict()
        track_tag_dict['artist'] = artist.title()
        track_tag_dict['album'] = album.title()
        track_tag_dict['year'] = year
        track_tag_dict['title'] = title.title()
        track_tag_dict['genre'] = genre.title()
        track_tag_dict['comment'] = 'Generated by all new lossless2lossy.py!'
        track_tag_dict['disctotal'] = '1'
        if lossless_file is None:
            track_tag_dict['infile'] = f'split-track{track:02d}.wav'
        else:
            track_tag_dict['losslessfile'] = lossless_file
            filename, ext = os.path.splitext(lossless_file)
            track_tag_dict['infile'] = filename + '.wav'
        track_tag_dict['outfile'] = f'{track:02d} {slugify(title)}.m4a'
        if 1 not in tag_dict:
            tag_dict[1] = dict()
        tag_dict[1][track] = track_tag_dict

    if lossless_file is None:
        tag_dict['single_lossless_file'] = True
    else:
        tag_dict['single_lossless_file'] = False

    return tag_dict


def get_album_tags_from_dir(config):
    cwd = os.getcwd()
    audio_source_files = [f for f in os.listdir(cwd) if f.endswith('.ape')
                          or f.endswith('.wv')
                          or f.endswith('.flac')]
    tag_dict = dict()

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
            decode_stderr = subprocess.Popen(
                [config.other_tools[config.decoder], '-i', track_file, '-y', '-f', 'ffmetadata'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE).stderr

            for line in decode_stderr.readlines():
                if config.args.performer is None:
                    artist_match = re.match(r'^ +ARTIST +: +(.*)$', line.decode('utf-8'), re.IGNORECASE)
                    if artist_match is not None:
                        artist = artist_match.group(1)
                        continue
                else:
                    artist = config.args.performer

                if config.args.album is None:
                    album_match = re.match(r'^ +ALBUM +: +(.*)$', line.decode('utf-8'), re.IGNORECASE)
                    if album_match is not None:
                        album = album_match.group(1)
                        continue
                else:
                    album = config.args.album

                if config.args.year is None:
                    year_match = re.match(r' +DATE +: +([0-9][0-9][0-9][0-9]).?[0-9]?.?[0-9]?',
                                          line.decode('utf-8'), re.IGNORECASE)
                    if year_match is not None:
                        year = int(year_match.group(1))
                        continue
                else:
                    year = config.args.year

                disc_match = re.match(r'^ +disc +: +([0-9]+)$', line.decode('utf-8'),
                                           re.IGNORECASE)
                if disc_match is not None:
                    disc = int(disc_match.group(1))
                    continue

                disctotal_match = re.match(r'^ +DISCTOTAL +: +([0-9]+)$', line.decode('utf-8'),
                                           re.IGNORECASE)
                if disctotal_match is not None:
                    disctotal = int(disctotal_match.group(1))
                    continue

                title_match = re.match(r'^ +title +: +(.*)$', line.decode('utf-8'), re.IGNORECASE)
                if title_match is not None:
                    title = title_match.group(1)
                    continue

                if config.args.genre is None:
                    genre_match = re.match(r'^ +GENRE +: +(.*)$', line.decode('utf-8'), re.IGNORECASE)
                    if genre_match is not None:
                        genre = genre_match.group(1)
                        continue
                else:
                    genre = config.args.genre

                track_match = re.match(r'^ +track +: +(.*)$', line.decode('utf-8'), re.IGNORECASE)
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

    tag_dict['single_lossless_file'] = False

    return tag_dict


def extract_single_lossless_file(single_lossless_file, cuefile):
    if not single_lossless_file:
        return None
    with open(cuefile) as cuefile_fd:
        lossless_file = None
        for cuefile_line in cuefile_fd.readlines():
            lossless_file_match = re.match(r'^ *\t*FILE *\t*"(.*)" *(WAVE)?(FLAC)?(APE)? *\t*$', cuefile_line, re.IGNORECASE)
            if lossless_file_match is not None:
                if lossless_file is not None:
                    return None
                else:
                    lossless_file = lossless_file_match.group(2)
    return None


def decode_input_files(config, tag_dict, cuefile=None, lossless_file=None):
    if tag_dict['single_lossless_file']:
        print('A single lossless file was found! Splitting it...')
        decode_cmd = config.decode_tools[config.splitter].copy()

        if config.splitter == 'shntool_bin':
            decode_cmd.append('-f')
            decode_cmd.append(cuefile)
            decode_cmd.append('-d')
            decode_cmd.append('.')
            decode_cmd.append('-o')
            decode_cmd.append('wav')
            decode_cmd.append('-O')
            decode_cmd.append('always')
            decode_cmd.append(lossless_file)

        decode_stdout = subprocess.Popen(decode_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
    elif 1 not in tag_dict:
        print('No files containing tags found! Leaving decode function...')
    else:
        print('The referenced cuefile contains multiple files. Converting one by one...')
        decode_cmd = config.decode_tools[config.decoder].copy()

        for disc in tag_dict:
            for track in tag_dict[disc]:
                try:
                    losslessfile = track['losslessfile']
                except KeyError as key_error:
                    print('the tag dict does not contain a losslessfile field in each track...')
                    raise key_error

                if config.splitter == 'ffmpeg_bin':
                    decode_cmd.append('-i')
                    decode_cmd.append(losslessfile)
                    decode_cmd.append(track['infile'])

                decode_stdout = subprocess.Popen(decode_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def compose_converter_cmd(config, tags, dir_name):
    infile = tags['infile']
    outfile = os.path.join(dir_name, tags['outfile'])

    if config.encoder == 'afconvert_bin':
        encoder_cmd = config.encode_tools[config.encoder].copy()
        encoder_cmd.append('-b')
        encoder_cmd.append(config.args.bitrate)
        encoder_cmd.append(infile)
        encoder_cmd.append(outfile)
    elif config.encoder == 'ffmpeg_bin':
        encoder_cmd = config.encode_tools[config.encoder].copy()
        encoder_cmd.append(infile)
        encoder_cmd.append(outfile)
    else:
        raise NotImplementedError()
    return encoder_cmd


def compose_tagger_cmd(config, track, n_tracks, disc, n_discs, tags, dir_name):
    outfile = os.path.join(dir_name, tags['outfile'])

    tagger_cmd = config.other_tools[config.tagger].copy()
    if config.tagger == 'atomicparsley_bin':
        tagger_cmd.append('--tracknum')
        tagger_cmd.append('"' + track + '/' + n_tracks + '"')
        tagger_cmd.append('--title')
        tagger_cmd.append(tags['title'])
        tagger_cmd.append('--artist')
        tagger_cmd.apppend(tags['artist'])
        tagger_cmd.append('--album')
        tagger_cmd.append(tags['album'])
        tagger_cmd.append('--genre')
        tagger_cmd.append(tags['genre'])
        tagger_cmd.append('--year')
        tagger_cmd.append(tags['year'])
        tagger_cmd.append('--comment')
        tagger_cmd.append(tags['comment'])
        if n_discs < 2 and (config.args.discs is None or config.args.discs < 2):
            tagger_cmd.append('--disk')
            if config.args.disc is not None:
                disc = config.args.disc
            if config.args.discs is not None:
                n_discs = config.args.discs
            tagger_cmd.append('"' + disc + '/' + n_discs + '"')
        if config.args.cover is not None:
            tagger_cmd.append('--artwork')
            tagger_cmd.append(config.args.cover)
        tagger_cmd.append(outfile)
    else:
        raise NotImplementedError()


def convert_files(album_tags, config):
    if 1 not in album_tags:
        print('No files containing tags found! Leaving convert function...')
        return

    if config.args.path is not None and os.path.isdir(config.args.path):
        dir_name = config.args.path
    else:
        dir_name = os.getcwd()

    dir_name = os.path.join(dir_name, config.args.album)
    try:
        os.stat(dir_name)
    except:
        os.mkdir(dir_name)

    n_discs = len(album_tags)
    for disc, tracktags in album_tags.items():
        n_tracks = len(tracktags)
        for track, tags in tracktags.items():
            print()
            print('converting track {}/{} of disc {}/{}...'.format(track, n_tracks, disc, n_discs))
            print('cmd line is ')
            print()

            converter_cmd = compose_converter_cmd(config, tags, dir_name)
            output_cmd = ''
            for param in converter_cmd:
                output_cmd.append(param + ' ')
            print(output_cmd)
            convert_stdout = subprocess.Popen(converter_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

            tagger_cmd = compose_tagger_cmd(config, track, n_tracks, disc, n_discs, tags, dir_name)
            output_cmd = ''
            for param in tagger_cmd:
                output_cmd.append(param + ' ')
            print(output_cmd)
            tagging_stdout = subprocess.Popen(tagger_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def main():
    args = parser()
    config = create_config(args=args)
    # check = check_tools(config)
    check = True

    if not check:
        return -1

    ret = select_cuefile(args.cuefile)
    album_tags = None

    if ret[0] == 1:
        print('trying file by file mode...')
        album_tags = get_album_tags_from_dir(config)
        decode_input_files(config, album_tags)
    elif ret[0] == -1:
        return -1
    elif ret[0] == 0:
        cuefile = ret[1]
        album_tags = get_album_tags_from_cuefile(cuefile, config)
        single_lossless_file = extract_single_lossless_file(album_tags['single_lossless_file'], cuefile)
        decode_input_files(config, album_tags, cuefile, single_lossless_file)

    convert_files(album_tags, config)
    return 0


if __name__ == '__main__':
    main()
