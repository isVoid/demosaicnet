import os
import threading
import subprocess
import argparse

from tqdm import tqdm

maxConcurrentThreads = 5
# Disable subprocess call output
FNULL = open(os.devnull, 'w')
cmdf = "python %s --input %s --output %s --model %s --offset_x %d --offset_y %d"

verbose = False

def sq(s):
    # Escpae Bash Scripts
    return "'" + s.replace("'", "'\\''") + "'"

class runMyBash (threading.Thread):
   def __init__(self, cmd):
      threading.Thread.__init__(self)
      self.cmd = cmd

   def run(self):
       if not verbose:
           subprocess.call(self.cmd, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)
       else:
           subprocess.call(self.cmd, shell=True)


def batch_demosaic_with_djdd(dir, output, dem_bin = "./bin/demosaic", model = "./pretrained_models/bayer/"
    , offx = "1", offy = "0", gpu = True):

    for (root, dirnames, filenames) in os.walk(dir):
        if not verbose:
            pbar = tqdm(total = len(filenames))
        for name in filenames:
            while (threading.activeCount() > maxConcurrentThreads):
                pass #Avoid too many workers.
            f = root + name
            if not gpu:
                cmd = cmdf % (sq(dem_bin), sq(f), sq(output), sq(model), offx, offy)
            else:
                cmd = cmdf % (sq(dem_bin), sq(f), sq(output), sq(model), offx, offy) + " --gpu"
            # print cmd
            bashThr = runMyBash(cmd=cmd)
            bashThr.start()
            if not verbose: pbar.update(1)

    while (threading.activeCount() > 1):
        pass #Block till all workers finishes.

    if not verbose: pbar.close


def main(args):

    global verbose
    verbose = args.verbose

    mosaic_dir = args.mosaic_dir
    output_dir = args.output_dir

    if not os.path.exists(mosaic_dir):
        raise ValueError("Mosaics: %s does not exists." % mosaic_dir)
    if not os.path.exists(output_dir):
        raise ValueError("Outputs: %s does not exists." % output_dir)

    dem_bin = args.bin
    model = args.model
    if not os.path.exists(dem_bin):
        raise ValueError("Executable: %s does not exists." % dem_bin)
    if not os.path.exists(model):
        raise ValueError("Model: %s does not exists." % model)

    offx = args.offx
    offy = args.offy
    gpu = args.gpu

    assert type(offx) is int, "Wrong offset_x type"
    assert type(offy) is int, "Wrong offset_y type"
    assert type(gpu) is bool, "Wrong gpu flag type"


    batch_demosaic_with_djdd(dir = mosaic_dir, output = output_dir, dem_bin = dem_bin,
        model = model, offx = offx, offy = offy, gpu = gpu)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "Utility to batch perform \"deep joint demosaic and denoising\"")

    parser.add_argument("mosaic_dir", type = str, help = "Folder that contains a list of mosaics")
    parser.add_argument("output_dir", type = str, help = "Folder to hold output demosaicked files")
    parser.add_argument("--bin", default = "bin/demosaick", type = str, help = "Executable of deep joint demosaic and denoising")
    parser.add_argument("--model", default = "pretrained_models/bayer/", type = str, help = "Model to use for demosaic")
    parser.add_argument("--offx", default = 0, type = int, help = "Offset x to align mosaic")
    parser.add_argument("--offy", default = 0, type = int, help = "Offset y to align mosaic")
    parser.add_argument("--gpu", dest='gpu', action='store_true', help = "Use GPU to demosaic")
    parser.add_argument("--verbose", dest='verbose', action='store_true', help = "Verbose output")

    args = parser.parse_args()

    main(args)
