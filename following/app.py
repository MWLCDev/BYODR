import time
import torch
import sys 

if __name__ == "__main__":
    while True:
        print("Python Version:", sys.version)
        print(torch.cuda.is_available())
        print(torch.version.cuda)
        print(torch.__version__)
        time.sleep(40)
