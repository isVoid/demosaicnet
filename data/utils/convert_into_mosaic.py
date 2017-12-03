from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Imports
import numpy as np
from PIL import Image
from tqdm import tqdm

import argparse
import os
import re
import subprocess
import threading

params = {}

rgbg = "-r %.3f %.3f %.3f %.3f"
dcraw_cmd = "dcraw%s -d -6 -T %s %s"
libraw_cmd = "dcraw_emu %s -disinterp -6 -T -o 0 %s"

def build_cmd(image_path):
    global params, rgbg, dcraw_cmd, libraw_cmd
    DECODER = params['DECODER']
    if params['W']:
        W = ' -W'
    else:
        W = ''

    if params['r'] is not None:
        r = params['r']
        rgb_mtplr = rgbg % (r[0], r[1], r[2], r[3])
    else:
        rgb_mtplr = ''

    if DECODER == 'dcraw':
        cmd = dcraw_cmd % (W, rgb_mtplr, re.escape(image_path))

    elif DECODER == 'libraw':
        cmd = libraw_cmd % (rgb_mtplr, re.escape(image_path))

    else:
        raise NotImplementedError("Unindentifed decoder")

    return cmd

def convert_into_mosaic(image_path):
    """Convert the image into mosaic with libraw:
        Input:
            a single image path

        File output:
            follows the output of
            dcraw -W -d -6 -T
            or
            dcraw_emu -r 1 1 1 1 -disinterp -6 -T -o 0

        Return:
            code, return code of dcraw_emu. non zero on error.
    """

    cmd = build_cmd(image_path)
    code = subprocess.call(cmd, shell=True)
    return code

def batch_convert(image_path_list):
    """Iterate image path list and apply dcraw_emu conversion of the images:
        Input:
            image_path_list: a list of images to convert, in full fs path

        Return: None
    """

    print ("Starting to convert.")
    for img in tqdm(image_path_list):
            c = convert_into_mosaic(img)

def batch_convert_multi(image_path_list):
    """Iterate image path list and apply dcraw_emu conversion of the images: (multi_threaded)
        Input:
            image_path_list: a list of images to convert, in full fs path
        Calls:
            convert_into_mosaic()
        Return:
            None
    """

    max_thread = 32

    print ("Starting to convert.")
    for img in tqdm(image_path_list):
        while (threading.active_count() > max_thread):
            pass #Wait till some thread finishes.

        t = threading.Thread(target = convert_into_mosaic, args = (img, ))
        t.start()

    while(threading.active_count() > 1):
        pass #Wait till all thread finishes.


def move_to_dst(img_list, dst, cn):
    """Move all mosaic image to dst folder
        Input:
            img_list: list of images that needed to be moved
            dst: destination folder, specified in output parameter
            cn: clean/noisy indicator
        Output:
            None
    """

    n = 0
    for _, _, files in os.walk(dst):
        n = len(files)

    filename = ""

    print ("Moving outputs to destination.")
    for i in tqdm(img_list):
        # filename = i.split("/")[-1]
        if cn == 'c':
            filename = "c%s.tiff" % str(n).zfill(6)
        elif cn == 'n':
            filename = "n%s.tiff" % str(n).zfill(6)
        elif cn == 't':
            filename = "t%s.tiff" % str(n).zfill(6)
        os.rename(i, dst+filename)
        n+=1


def get_file_list(dir, regex=None):
    """Get List of files from directory

        Input: DIR, directory to retrieve content from
        regex: the regex used to filter out unwanted files

        Return:
            filename_list, list of contents filename, sorted by sorted()

    """

    if not os.path.exists(dir):
        raise IOError("%s does not exsit." % dir)

    filename_list = []

    for root, _ , files in os.walk(dir):
        files = sorted(files)
        for f in files:
            if regex is None or regex.match(f):
                filename_list.append(root + f)

    return filename_list


def main(args):

    global params
    src = args.dir
    out = args.output
    test = args.test


    if args.libraw:
        if args.W:
            raise NotImplementedError("Cannot use -W with libraw")

        print ("Using libraw as raw decoder.")
        params['DECODER'] = 'libraw'

    else:
    	print ("Using dcraw as raw decoder.")
    	params['DECODER'] = 'dcraw'


    if args.W:
        print ("Will not auto brighten image.")
        params['W'] = True
    else:
        print ("Will brighten image.")
        params['W'] = False

    if args.r:
    	print ("Use specified rgbg multipliers %s" % str(args.r))
    	params['r'] = args.r
    else:
        print ("Use default rgbg multiplier.")
        if params['DECODER'] == 'libraw':
            params['r'] = [1, 1, 1, 1]
        else:
            params['r'] = None


    if not test:
        # Converting training set
        cdir = "Clean/"
        ndir = "Noisy/"

        csrc = src + cdir
        nsrc = src + ndir

        cout = out + cdir
        nout = out + ndir

        if not os.path.exists(cout):
            os.mkdir(cout)
        if not os.path.exists(nout):
            os.mkdir(nout)

        arwregex = re.compile(r'.*\.ARW')
        cimage_list = get_file_list(csrc, arwregex)
        nimage_list = get_file_list(nsrc, arwregex)

        if not len(cimage_list) == len(nimage_list):
            raise Exception("Sanity check: File counts mismatch of %s" % src)

        batch_convert_multi(cimage_list)
        batch_convert_multi(nimage_list)

        tiffregex = re.compile(r'.*\.tiff')
        coutput_list = get_file_list(csrc, tiffregex)
        noutput_list = get_file_list(nsrc, tiffregex)

        if not len(coutput_list) == len(noutput_list):
            raise Exception("Sanity check: Mosaic files counts mismatch")

        move_to_dst(coutput_list, cout, 'c')
        move_to_dst(noutput_list, nout, 'n')

    else:
        # Converting test set
        print ("Converting test set.")

        if not os.path.exists(out):
            os.mkdir(out)

        arwregex = re.compile(r'.*\.ARW')
        image_list = get_file_list(src, arwregex)

        batch_convert_multi(image_list)

        tiffregex = re.compile(r'.*\.tiff')
        output_list = get_file_list(src, tiffregex)

        move_to_dst(output_list, out, 't')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "Helper function to extract patches for deepdenoisenet")

    parser.add_argument('dir', type = str, help = "Directory of input images, ARW only.")
    parser.add_argument('output', type = str, help = "Directory to mosaic tiff output.")
    parser.add_argument('--test', dest='test', action='store_true', help = "If defined, will only batch convert single folder.")
    parser.add_argument('--libraw', dest='libraw', action='store_true', help = "Use dcraw_emu instead of dcraw to convert.")
    parser.add_argument('--W', dest='W', action='store_true', help='Don\'t auto brighten image')
    parser.add_argument('--r', type = float,nargs=4, help = 'Use specified rgbg multipliers.')

    args = parser.parse_args()

    main(args)
