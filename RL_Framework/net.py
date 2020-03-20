import torch
import torch.nn as nn
import torch.nn.functional as F
import os
from constants import TrainingConstants

torch.set_default_dtype(torch.float64)

class Net(nn.Module):
    def __init__(self, input_cc_mean, input_cc_std, input_raw_mean, input_raw_std, name='alpha_net'):
        super(Net, self).__init__()
        self.name = name
        self.input_cc_mean = input_cc_mean
        self.input_cc_std = input_cc_std
        self.input_raw_mean = input_raw_mean
        self.input_raw_std = input_raw_std
        self._device = TrainingConstants.DEVICE

        self.cc_conv1 = nn.Conv2d(in_channels=3, out_channels=16, stride=1, kernel_size=5, padding=2)
        self.cc_bn1 = nn.BatchNorm2d(16) 
        self.cc_conv2 = nn.Conv2d(16, 32, stride=1, kernel_size=3, padding=1)
        self.cc_bn2 = nn.BatchNorm2d(32)
        self.cc_pool = torch.nn.MaxPool2d(kernel_size=2, stride=2, padding=0)
        self.cc_fc = nn.Linear(62, 16)

        self.raw_conv1 = nn.Conv2d(in_channels=12, out_channels=32, stride=1, kernel_size=5, padding=2)
        self.raw_bn1 = nn.BatchNorm2d(32)
        self.raw_conv2 = nn.Conv2d(32, 64, stride=1, kernel_size=3, padding=1)
        self.raw_bn2 = nn.BatchNorm2d(64)
        self.raw_pool = torch.nn.MaxPool2d(kernel_size=2, stride=2, padding=0)
        self.raw_fc = nn.Linear(15, 8)

        self.fc = nn.Linear(TrainingConstants.FLAT_STATE_DIM, TrainingConstants.ACT_DIM)
        

    def forward(self, x):
        max_y = max(TrainingConstants.CC_IMG_DIMS[2], TrainingConstants.RAW_DIMS[2], TrainingConstants.GLOBAL_CC_DIMS[2])
        cc_sector = x[:,:,:,:max_y][:,:TrainingConstants.CC_IMG_DIMS[0],:TrainingConstants.CC_IMG_DIMS[1],:TrainingConstants.CC_IMG_DIMS[2]]
        water_and_plants = x[:,:,:,max_y:max_y*2][:,:TrainingConstants.RAW_DIMS[0],:TrainingConstants.RAW_DIMS[1],:TrainingConstants.RAW_DIMS[2]]
        global_cc = x[:,:,:,max_y*2:][:,:TrainingConstants.GLOBAL_CC_DIMS[0],:TrainingConstants.GLOBAL_CC_DIMS[1],:TrainingConstants.GLOBAL_CC_DIMS[2]]
        
        cc_normalized = (cc_sector - torch.tensor(self.input_cc_mean, dtype=torch.float32, device=self._device)) / torch.tensor(self.input_cc_std, dtype=torch.float32, device=self._device)
        cc = self.cc_conv1(cc_normalized)
        cc = self.cc_bn1(cc)
        cc = F.relu(cc)
        cc = self.cc_conv2(cc)
        cc = self.cc_bn2(cc)
        cc = F.relu(cc)
        cc = self.cc_pool(cc)
        cc = self.cc_fc(cc)

        water_and_plants_normalized = (water_and_plants - torch.tensor(self.input_raw_mean[1], dtype=torch.float32, device=self._device)) / torch.tensor(self.input_raw_std[1], dtype=torch.float32, device=self._device)
        raw = self.raw_conv1(water_and_plants_normalized)
        raw = self.raw_bn1(raw)
        raw = F.relu(raw)
        raw = self.raw_conv2(raw)
        raw = self.raw_bn2(raw)
        raw = F.relu(raw)
        raw = self.raw_pool(raw)
        raw = self.raw_fc(raw)
        print("cc, raw ", cc.size(), raw.size())
        cc = cc.reshape((cc.shape[0], -1))
        raw = raw.reshape((raw.shape[0], -1))
        print("cc, raw ", cc.size(), raw.size())
        cc_and_raw = torch.cat((cc, raw), dim=1)
        print("cc_and_raw - ", cc_and_raw.size())
        global_cc_normalized = (global_cc - torch.tensor(self.input_raw_mean[0], dtype=torch.float32, device=self._device)) / torch.tensor(self.input_raw_std[0], dtype=torch.float32, device=self._device)
        print("global_cc_normalized - ", global_cc_normalized.size())
        global_cc_normalized = global_cc_normalized.reshape((global_cc_normalized.shape[0], -1))
        state = torch.cat((cc_and_raw, global_cc_normalized), dim=1)
        state = F.relu(state)
        print("state.size: ", state.size())
        action = self.fc(state)
        return action

    def save(self, dir_path, net_fname):
        net_path = os.path.join(dir_path, net_fname)
        moments_path = os.path.join(dir_path, 'moments.txt') ## TODO: save all moments you used
        torch.save(self.state_dict(), net_path)
        with open(moments_path, 'w+') as mfile:
            mfile.write(str(self.input_cc_mean) + ', ' + str(self.input_cc_std))
            mfile.write(str(self.input_raw_mean) + ', ' + str(self.input_raw_std))

    def load(self, dir_path, net_fname):
        net_path = os.path.join(dir_path, net_fname)
        moments_path = os.path.join(dir_path, 'moments.txt')
        state_dict = torch.load(net_path)
        self.load_state_dict(state_dict)
        with open(moments_path) as mfile:
            moments = mfile.readlines()
            self.input_cc_mean = [float(val) for val in moments[0].split()[1:-1]] ## TODO: parse all moments
            self.input_cc_std = [float(val) for val in moments[1].split()[1:-1]]
            self.input_raw_mean = [float(val) for val in moments[0].split()[1:-1]]
            self.input_raw_std = [float(val) for val in moments[1].split()[1:-1]]