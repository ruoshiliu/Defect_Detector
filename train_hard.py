import pandas as pd
import numpy as np
import torch, torchvision
from torch.utils.data import Dataset, DataLoader
import torch.nn as nn
import torch.optim as optim
from torch.optim import lr_scheduler
from torch.autograd import Variable
from torchvision import datasets, models, transforms
from grayscale_resnet import resnet18, resnet34, resnet50, resnext50_32x4d
from train import train_model

window_size = 45
pad_size = window_size
classes = ["pos","neg"] # classes has to match the 'classes' column in labels csv
output_path = '/home/rliu/defect_classifier/models/python/res34-600epo_hard_01-10-18.model'
batch_size = 256
non_pos_ratio = 1
train_num = 10000
test_num = 2000
mode = 'full' # or "tiny"
method = 'hard'
num_epochs = 600
df_train_path = '/home/rliu/TDD-Net/csv_labels/112000train_pos_neg.csv'
df_test_path = '/home/rliu/TDD-Net/csv_labels/112000test_pos_neg.csv'

data_transform = transforms.Compose([
        transforms.RandomResizedCrop(200, scale=(1, 1), ratio=(1, 1)),
        transforms.RandomRotation((-90,90)),
        torchvision.transforms.RandomVerticalFlip(p=0.5),
        torchvision.transforms.RandomHorizontalFlip(p=0.5),
        torchvision.transforms.RandomAffine(180, shear = 20),
        torchvision.transforms.RandomPerspective(distortion_scale=0.1, p=0.1, interpolation=3),
        torchvision.transforms.ColorJitter(brightness=0.5, contrast=0.5, saturation=0, hue=0)])

use_gpu = torch.cuda.is_available()
if use_gpu:
    print("GPU in use")

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

# transfer learning resnet34
if mode == "full":
    model = resnet34()
elif mode == "tiny":
    model = resnet18()
elif mode == "next":
    model = resnext50_32x4d()

# change output channel for last fully connected layer according to number of classes
num_ftrs = model.fc.in_features
model.fc = nn.Linear(num_ftrs, len(classes)+1) # number of classes plus negative samples 

if use_gpu:
    model = torch.nn.DataParallel(model)
    model.to(device)

# adjust weights of negative samples during training
weights = []
for i in range(len(classes)):
    weights.append(1.0)
weights.append(1.0/non_pos_ratio)

class_weights = torch.FloatTensor(weights).to(device)

criterion = nn.NLLLoss(weight = class_weights)
# optimizer = optim.SGD(model.parameters(), lr=0.01,  momentum=0.9)
optimizer = optim.Adam(model.parameters(), lr=0.00025, weight_decay=0)

# Decay LR by a factor of 0.1 every 7 epochs
exp_lr_scheduler = lr_scheduler.StepLR(optimizer, step_size=100, gamma=0.5)

# train model
model = train_model(model, criterion, optimizer, exp_lr_scheduler, data_transform, train_num = train_num, test_num = test_num, non_pos_ratio = non_pos_ratio, window_size = window_size, batch_size = batch_size, device = device, classes = classes, df_train_path = df_train_path, df_test_path = df_test_path, num_epochs=num_epochs, method = method)
torch.save(model.module, output_path)