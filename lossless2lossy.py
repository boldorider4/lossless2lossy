#!/usr/bin/python3

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
        self.single_lossless_file = None
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
    config.decode_tools = { 'flac_bin' : ['flac'],
                            'shntool_bin' : ['shntool', 'split', '-o', 'wav', '-O', 'always'],
                            'ffmpeg_bin' : ['ffmpeg'],
                            'mac_bin' : ['mac'],
                            'wvunpack_bin' : 'wvunpack' }
    config.encode_tools = { 'ffmpeg_bin' : ['ffmpeg'],
                            'afconvert_bin' : ['afconvert', '-v', '-d', 'aac', '-f', 'm4af', '-u', 'pgcm', '2', '-q',
                                               '127', '-s', '2', '--soundcheck-generate'] }
    config.other_tools = { 'mp4box_bin' : ['mp4box'],
                           'ffmpeg_bin' : ['ffmpeg'],
                           'cueprint_bin' : ['cueprint'],
                           'atomicparsley_bin' : ['AtomicParsley', '--overWrite'] }
    config.decoder = 'ffmpeg_bin'
    config.encoder = 'afconvert_bin'
    config.splitter = 'shntool_bin'
    config.tagger = 'atomicparsley_bin'
    return config


def subprocess_popen(cmd):
    try:
        env_path = dict()
        env_path['PATH'] = os.environ['PATH']
        env_path['PATH'] = '/usr/local/bin:' + env_path['PATH']
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env_path, shell=False)
    except FileNotFoundError as file_not_found_error:
        print('something went wrong when trying to run {}'.format(cmd))
        print(file_not_found_error)
        exit(-1)


def check_tools(config):
    
    # check other tools
    for tool in config.other_tools.values():
        proc = subprocess_popen(['which',tool[0]])
        proc.wait()
        if len(proc.stdout.readlines()) == 0:
            print('{} is missing and is required'.format(tool[0]))
            return False        

    # check decode tools
    is_any_tool_installed = False
    for tool in config.decode_tools.values():
        proc = subprocess_popen(['which',tool[0]])
        proc.wait()
        is_any_tool_installed |= (len(proc.stdout.readlines()) > 0)
    if not is_any_tool_installed:
        error_msg = 'neither of '
        for tool in config.decode_tools.values():
            error_msg += tool[0] + ' '
        error_msg += 'is installed'
        print(error_msg)
        return False

    # check encode tools
    is_any_tool_installed = False
    for tool in config.encode_tools.values():
        proc = subprocess_popen(['which',tool[0]])
        proc.wait()
        is_any_tool_installed |= (len(proc.stdout.readlines()) > 0)
    if not is_any_tool_installed:
        error_msg = 'neither of '
        for tool in config.encode_tools.values():
            error_msg += tool[0] + ' '
        error_msg += 'are installed'
        print(error_msg)
        return False

    return True


def select_cuefile(args):
    cwd = os.getcwd()
    cuefile = args.cuefile
    if cuefile is not None:
        cuefile = os.path.abspath(args.cuefile)
        if os.stat(cuefile) and os.path.isfile(cuefile):
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
    config.args.cover = os.path.abspath(config.args.cover)
    if config.args.cover is None or not (os.stat(config.args.cover) or os.path.isfile(config.args.cover)):
        print('warning: cover file does not exist or is not a valid file')
        config.args.cover = None


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


def detect_cuefile_encoding(cuefile):
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


def fix_coding_issue(line, encoding):
    decoded_line = line.decode(encoding)
    if encoding == 'cp1252':
        decoded_line = decoded_line.replace('’', '\'', )
    return decoded_line


def get_album_tags_from_cuefile(cuefile, config):
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
                year_match = re.match(r'^ *\t*(REM )?DATE *\t*([0-9]*) *$', cuefile_line, re.IGNORECASE)
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
            decode_subprocess = subprocess_popen(
                [config.other_tools[config.decoder], '-i', track_file, '-y', '-f', 'ffmetadata'])
            decode_subprocess.wait()
            decode_stderr = decode_subprocess.stderr

            for line in decode_stderr.readlines():
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

    config.single_lossless_file = False

    return tag_dict


def extract_single_lossless_file(cuefile, config):
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


def decode_input_files(config, tag_dict, cuefile=None, single_lossless_file=None):
    if config.single_lossless_file:
        print('A single lossless file was found! Splitting it...')
        decode_cmd = config.decode_tools[config.splitter].copy()

        if config.splitter == 'shntool_bin':
            decode_cmd.append('-f')
            decode_cmd.append(cuefile)
            decode_cmd.append('-d')
            decode_cmd.append('.')
            decode_cmd.append(single_lossless_file)

        return [subprocess_popen(decode_cmd)]
    elif 1 not in tag_dict:
        print('No files containing tags found! Leaving decode function...')
        exit(-1)
    else:
        print('The referenced cuefile contains multiple files. Converting one by one...')
        decode_cmd = config.decode_tools[config.decoder].copy()

        decode_stdout = list()

        for disc in tag_dict:
            for n_track, track in tag_dict[disc].items():
                try:
                    losslessfile = track['losslessfile']
                except KeyError as key_error:
                    print('the tag dict does not contain a losslessfile field in each track...')
                    raise key_error

                if config.splitter == 'ffmpeg_bin':
                    decode_cmd.append('-i')
                    decode_cmd.append(losslessfile)
                    decode_cmd.append(track['infile'])

                decode_stdout.append(subprocess_popen(decode_cmd))
        return decode_stdout


def compose_converter_cmd(config, tags, dir_name):
    infile = tags['infile']
    outfile = os.path.join(dir_name, tags['outfile'])
    if config.args.bitrate is None:
        bitrate = str(256000)
    else:
        bitrate = config.args.bitrate

    if config.encoder == 'afconvert_bin':
        encoder_cmd = config.encode_tools[config.encoder].copy()
        encoder_cmd.append('-b')
        encoder_cmd.append(bitrate)
        encoder_cmd.append(infile)
        encoder_cmd.append(outfile)
    elif config.encoder == 'ffmpeg_bin':
        encoder_cmd = config.encode_tools[config.encoder].copy()
        encoder_cmd.append(infile)
        encoder_cmd.append(outfile)
    else:
        raise NotImplementedError()
    return encoder_cmd


def append_option_to_cmd(cmd, option, tag):
    if tag is not None and isinstance(tag, str) and tag != '':
        cmd.append(option)
        cmd.append(tag)


def compose_tagger_cmd(config, track, n_tracks, disc, n_discs, tags, dir_name):
    outfile = os.path.join(dir_name, tags['outfile'])

    tagger_cmd = config.other_tools[config.tagger].copy()
    if config.tagger == 'atomicparsley_bin':
        tagger_cmd.insert(1, outfile)
        tagger_cmd.append('--tracknum')
        tagger_cmd.append(str(track) + '/' + str(n_tracks))
        append_option_to_cmd(tagger_cmd, '--title', tags['title'])
        append_option_to_cmd(tagger_cmd, '--artist', tags['artist'])
        append_option_to_cmd(tagger_cmd, '--album', tags['album'])
        append_option_to_cmd(tagger_cmd, '--genre', tags['genre'])
        append_option_to_cmd(tagger_cmd, '--year', tags['year'])
        append_option_to_cmd(tagger_cmd, '--comment', tags['comment'])
        if n_discs > 1 or (config.args.discs is not None and config.args.discs > 1):
            tagger_cmd.append('--disk')
            if config.args.disc is not None:
                disc = config.args.disc
            if config.args.discs is not None:
                n_discs = config.args.discs
            tagger_cmd.append(str(disc) + '/' + str(n_discs))
        if config.args.cover is not None:
            tagger_cmd.append('--artwork')
            tagger_cmd.append(config.args.cover)
    else:
        raise NotImplementedError()

    return tagger_cmd


def convert_files(album_tags, config):
    if 1 not in album_tags:
        print('No files containing tags found! Leaving convert function...')
        exit(-1)

    if config.args.path is not None and os.path.isdir(config.args.path):
        dir_name = config.args.path
    else:
        dir_name = os.getcwd()

    global_album = album_tags[1][1]['album']
    dir_name = os.path.join(dir_name, global_album)
    try:
        os.stat(dir_name)
    except:
        os.mkdir(dir_name)

    n_discs = len(album_tags)
    tagging_subprocess = list()
    converting_subprocess = list()
    for disc, tracktags in album_tags.items():
        n_tracks = len(tracktags)
        for track, tags in tracktags.items():
            print()
            print('converting track {}/{} of disc {}/{}...cmd line is'.format(track, n_tracks, disc, n_discs))

            converter_cmd = compose_converter_cmd(config, tags, dir_name)
            output_cmd = ''
            for param in converter_cmd:
                output_cmd += param + ' '
            print(output_cmd)

            converting_subprocess.append(subprocess_popen(converter_cmd))

    for convert_subprocess in converting_subprocess:
        convert_subprocess.wait()

    for disc, tracktags in album_tags.items():
        n_tracks = len(tracktags)
        for track, tags in tracktags.items():
            print('cleaning up temp file...')
            os.remove(tags['infile'])

            print('taggin track track {}/{} of disc {}/{}...'.format(track, n_tracks, disc, n_discs))

            tagger_cmd = compose_tagger_cmd(config, track, n_tracks, disc, n_discs, tags, dir_name)
            output_cmd = ''
            for param in tagger_cmd:
                output_cmd += param + ' '
            print(output_cmd)
            tagging_subprocess.append(subprocess_popen(tagger_cmd))

    for tagging_subproc in tagging_subprocess:
        tagging_subproc.wait()

    if config.args.cover is not None and config.tagger == 'atomicparsley_bin':
        cover_filename, cover_ext = os.path.splitext(config.args.cover)
        cover_residue = os.path.basename(cover_filename + '-resized')
        for filename in os.listdir(os.getcwd()):
            if filename.startswith(cover_residue) and (filename.endswith('.jpeg') or \
                                                        filename.endswith('.jpg') or \
                                                        filename.endswith('.png') or filename.endswith(cover_ext)):
                os.remove(filename)


def main():
    args = parser()
    config = create_config(args=args)
    check = check_tools(config)

    if not check:
        return -1

    ret = select_cuefile(args)
    album_tags = None

    if ret[0] == 1:
        print('trying file by file mode...')
        album_tags = get_album_tags_from_dir(config)
        decode_input_files(config, album_tags)
    elif ret[0] == -1:
        return -1
    elif ret[0] == 0:
        cuefile = ret[1]
        config.cuefile_encoding = detect_cuefile_encoding(cuefile)
        album_tags = get_album_tags_from_cuefile(cuefile, config)
        single_lossless_file = extract_single_lossless_file(cuefile, config)
        piped_subprocess = decode_input_files(config, album_tags, cuefile, single_lossless_file)
        for process in piped_subprocess:
            process.wait()

    convert_files(album_tags, config)
    return 0


if __name__ == '__main__':
    main()
