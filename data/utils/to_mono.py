from PIL import Image
from tqdm import tqdm
import numpy as np

import os
import argparse

def to_monochrome(tri):
  """Utility to convert libraw 3 channel raw into single channel

    Input: Libraw image as numpy array, size (H, W, 3)
    Input Pattern:
        R Channel (0):
        R 0 R 0 R
        0 0 0 0 0
        R 0 R 0 R
        0 0 0 0 0
        R 0 R 0 R

        G Chennel (1):
        0 G 0 G 0
        G 0 G 0 G
        0 G 0 G 0
        G 0 G 0 G
        0 G 0 G 0

        B Chennel (2):
        B' 0 B' 0 B'
        0 B 0 B 0
        B' 0 B' 0 B'
        0 B 0 B 0
        B' 0 B' 0 B'

    Output: Image squeezed into single channel, size (H, W)
    Bayer pattern:
        R G R G R
        G B G B G
        R G R G R
        G B G B G
        R G R G R
  """
  # monochromatic
  mo = np.zeros((tri.shape[0], tri.shape[1])).astype("uint8")

  # sqeeze
  mo[0::2,0::2] = tri[0::2, 0::2, 0]    #R
  mo[1::2,0::2] = tri[1::2, 0::2, 1]    #G1
  mo[0::2,1::2] = tri[0::2, 1::2, 1]    #G1
  b = tri[1::2, 1::2, 2] > tri[0::2, 0::2, 2]
  mo[1::2,1::2] = np.multiply(tri[1::2, 1::2, 2], b) + np.multiply(tri[0::2, 0::2, 2], 1-b) #max(B,B')

  # mo = np.sum(tri, axis = 2)
  assert len(mo.shape) == 2, "Output is not monochromatic"
  return mo

def get_image_list(li):
    """Utility to get all image from txt file

        Input: text file with all images to convert, each file path has one line.
        Output: a python list of file paths
    """
    with open(li) as f:
        filenames = f.readlines()

    filenames = [x.strip() for x in filenames]
    return filenames

def main(args):

    f = args.file
    o = args.output

    if not os.path.exists(o):
        os.mkdir(o)

    fl = []
    if f.split(".")[-1] == "txt":
        fl = get_image_list(f)
    else:
        fl.append(f)

    for img in tqdm(fl):
        i = np.array(Image.open(img))
        i = to_monochrome(i).astype("uint8")
        fn = img.split("/")[-1]
        Image.fromarray(i).save(o+fn)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "Utility to batch pack libraw trichromatic mosaics")

    parser.add_argument("file", help = "If text file, get all files in the text list, separated by return.")
    parser.add_argument("--output", "-o", help = "Output location", default = "./mono/")

    args = parser.parse_args()

    main(args)
