import os

batch = 18

d = "E:\\Pairs\\Batch%d\\" % batch

if not os.path.exists(d+"Clean\\"):
    os.mkdir(d+"Clean\\")
if not os.path.exists(d+"Noisy\\"):
    os.mkdir(d+"Noisy\\")

CleanCount = 0
NoisyCount = 0

flag = 1
# flag == 1, first frame is noisy
# flag == 0, first frame is clean
# Check before run.
# Generally first frame must be noisy, if not, think why.

for root, dirs, files in os.walk(d):
    print(root)
    for f in files:
        print(root + f)
        try:
            idx = int(f[3: 8])

            if (CleanCount + NoisyCount) % 2 == flag:
                os.rename(root + f, root + "\\Clean\\" + "Cleanb%d_" % batch + str(CleanCount).zfill(5) + ".ARW")
                CleanCount += 1
            else:
                os.rename(root + f, root + "\\Noisy\\" + "Noisyb%d_" % batch + str(NoisyCount).zfill(5) + ".ARW")
                NoisyCount += 1
        except Exception as inst:
            print ("Exception Raised, organizing finishes")
            print (type(inst))
            break
