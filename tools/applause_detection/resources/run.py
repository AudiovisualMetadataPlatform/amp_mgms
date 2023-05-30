import reader, feature, classifier, smoothing, writer
import sys
import os
import time
from amp_segment import AmpSegment 

if __name__ == '__main__':

    import argparse
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=__doc__
    )

    parser.add_argument(
        '-d', '--download',
        action='store_true',
        help='Flag to download input datasets; train and test sets for classifier & train set for word embedding.'
    )

    parser.add_argument(
        '-t', '--train',
        default='',
        action='store',
        nargs='?',
        help='Flag to invoke training pipeline. Use an argument to pass directory of training data. '
    )

    parser.add_argument(
        '-s', '--segment',
        default='',
        action='store',
        nargs=2,
        help='Flag to invoke segmentation pipeline. First arg to specify model path, and second to specify directory '
             'where files are.'
    )

    parser.add_argument(
        '-o', '--out',
        default='',
        action='store',
        help='Only valid with \'segment\' flag. When given, JSON files are '
             'generated from an input audio file, storing all segments and labels'
             'Generated files named after the full audio file in the directory provided.'
    )

    parser.add_argument(
        '-T', '--threshold',
        type=int,
        default='0',
        action='store',
        help='Minimum segment length in milliseconds.'
    )

    parser.add_argument(
        '-c', '--cpu',
        help='Ignore GPU, use CPU only'
    )

    parser.add_argument(
        '-b', '--binary',
        action='store_true',
        help='Flag to classifying applause/not-applause only.'
    )

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args = parser.parse_args()

    if args.cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

    if args.train:
        start = time.perf_counter()
        X, Y = feature.extract_all(reader.read_wavs(args.train), train=True, binary_class=args.binary)
        model_path = classifier.train_pipeline(X, Y)
        print("============")
        print(f"model saved at {model_path}")
        print(f"time elapsed: {time.perf_counter()-start:0.4f} seconds")
        print("============")

    if args.segment:
        # include 'dat' file extension for Galaxy data files
        for wav in reader.read_wavs(args.segment[1], file_ext=['mp3', 'wav', 'mp4', 'dat']):
            start = time.perf_counter()
            model = classifier.load_model(args.segment[0])
            predicted = classifier.predict_pipeline(wav, model)
            smoothed = smoothing.smooth(predicted, int(args.threshold), args.binary)
            amp_segments = AmpSegment(wav[1], smoothed)

            if args.out:
                writer.save_json(amp_segments, wav, args.out)
            print(f"Finished {wav} in {time.perf_counter()-start:0.4f} seconds")
