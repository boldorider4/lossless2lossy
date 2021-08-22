import os

from utility import subprocess_popen

class Codec:
    def __init__(self, config):
        self.config = config
        pass

    def decode_input_files(self, tag_dict, cuefile_object):
        config = self.config

        if config.single_lossless_file and cuefile_object.cuefile is not None:
            print('A single lossless file was found! Splitting it...')

            cuefile = cuefile_object.cuefile
            decode_cmd = config.decode_tools[config.splitter].copy()

            if config.splitter == 'shntool_bin':
                decode_cmd.append('-f')
                decode_cmd.append(cuefile)
                decode_cmd.append('-d')
                decode_cmd.append('.')
                decode_cmd.append(config.single_lossless_file_name)

            piped_subprocess = subprocess_popen(decode_cmd)
            piped_subprocess.wait()
        elif 1 not in tag_dict:
            print('No files containing tags found! Leaving decode function...')
            exit(-1)
        else:
            print('The referenced cuefile contains multiple files. Converting one by one...')

            piped_subprocess = list()

            for disc in tag_dict:
                for n_track, track in tag_dict[disc].items():
                    try:
                        losslessfile = track['losslessfile']
                    except KeyError as key_error:
                        print('the tag dict does not contain a losslessfile field in each track...')
                        raise key_error

                    infile = track['infile']
                    print('converting {} to {}'.format(os.path.basename(losslessfile), os.path.basename(infile)))

                    decode_cmd = config.decode_tools[config.decoder].copy()
                    if config.decoder == 'ffmpeg_bin':
                        decode_cmd.append('-i')
                        decode_cmd.append(losslessfile)
                        decode_cmd.append('-y')
                        decode_cmd.append(infile)

                    piped_subprocess.append(subprocess_popen(decode_cmd))

            for process in piped_subprocess:
                process.wait()

    def convert_files(self, album_tags):
        config = self.config

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
        print()
        for disc, tracktags in album_tags.items():
            n_tracks = len(tracktags)
            for track, tags in tracktags.items():
                print('converting track {}/{} of disc {}/{}...cmd line is'.format(track, n_tracks, disc, n_discs))

                converter_cmd = self._compose_converter_cmd(tags, dir_name)
                output_cmd = ''
                for param in converter_cmd:
                    output_cmd += param + ' '
                print(output_cmd)

                converting_subprocess.append(subprocess_popen(converter_cmd))

        for convert_subprocess in converting_subprocess:
            convert_subprocess.wait()

        print()
        for disc, tracktags in album_tags.items():
            n_tracks = len(tracktags)
            for track, tags in tracktags.items():
                print('cleaning up temp file...')
                os.remove(tags['infile'])

                print('taggin track track {}/{} of disc {}/{}...'.format(track, n_tracks, disc, n_discs))

                tagger_cmd = self._compose_tagger_cmd(track, n_tracks, disc, n_discs, tags, dir_name)
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

    def _compose_converter_cmd(self, tags, dir_name):
        config = self.config

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

    def _append_option_to_cmd(self, cmd, option, tag):
        if tag is not None and isinstance(tag, str) and tag != '':
            cmd.append(option)
            cmd.append(tag)

    def _compose_tagger_cmd(self, track, n_tracks, disc, n_discs, tags, dir_name):
        config = self.config
        outfile = os.path.join(dir_name, tags['outfile'])

        tagger_cmd = config.other_tools[config.tagger].copy()
        if config.tagger == 'atomicparsley_bin':
            tagger_cmd.insert(1, outfile)
            tagger_cmd.append('--tracknum')
            tagger_cmd.append(str(track) + '/' + str(n_tracks))
            self._append_option_to_cmd(tagger_cmd, '--title', tags['title'])
            self._append_option_to_cmd(tagger_cmd, '--artist', tags['artist'])
            self._append_option_to_cmd(tagger_cmd, '--album', tags['album'])
            self._append_option_to_cmd(tagger_cmd, '--genre', tags['genre'])
            self._append_option_to_cmd(tagger_cmd, '--year', tags['year'])
            self._append_option_to_cmd(tagger_cmd, '--comment', tags['comment'])
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