from __future__ import print_function, division
import os
import torch
import numpy as np
import matplotlib.pyplot as plt
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, utils
import cv2
import simplejson as json

class FMOWDataset(Dataset):
    """Functional Map of World Dataset"""
    """
    Total Data: 157378 images
    Residential Data: 18450 (13.28%)
    Non-residential Data: 138928 (86.72%)
    """

    def __init__(self, params, transform=None):
        """
        Args:
            params (dict): Dict containing key parameters of the project
            transform (callable, optional): Optional transform to be applied
                on a sample.
        """
        self.params = params
        self.transform = transform
        self.map = {}
        self.curr_index = 0
        def populate_map(category):
            path = os.path.join(params['dataset'], 'train', category)
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith('_rgb.jpg'):
                        image = os.path.join(root, file)
                        if not os.path.isfile(image):
                            continue
                        self.map[self.curr_index] = image
                        self.curr_index += 1
        res_count = 0
        non_res_count = 0
        for category in params['fmow_class_names_mini']:
            populate_map(category)
            
        # Populate a smaller map 
        size = 50000
        indices = np.random.choice(len(self.map), size, replace=False)
        self.mini_map = {}
        for i, idx in enumerate(indices):
            self.mini_map[i] = self.map[idx]
        self.map = self.mini_map

    def __len__(self):
        return len(self.map)

    def __getitem__(self, idx):
        image_p = self.map[idx]
        metadata_p = image_p[:-3] + 'json'
        try:
            image = cv2.imread(image_p, 0).astype(np.float32)
            m = open(metadata_p)
            metadata = json.load(m)
            m.close()
        except Exception as e:
            print("Exception: %s" % e)
        if isinstance(metadata['bounding_boxes'], list):
            metadata['bounding_boxes'] = metadata['bounding_boxes'][0]
        # Train only on first bounding box
        bb = metadata['bounding_boxes']
        
        box = bb['box']
        buffer = 16
        r1 = box[1] - buffer
        r2 = box[1] + box[3] + buffer
        c1 = box[0] - buffer
        c2 = box[0] + box[2] + buffer
        r1 = max(r1, 0)
        r2 = min(r2, image.shape[0])
        c1 = max(c1, 0)
        c2 = min(c2, image.shape[1])
        image = image[r1:r2, c1:c2, np.newaxis]
        
        label = np.ndarray([1,])
#         fmow_category = self.params['fmow_class_names'].index(bb['category'])         
#         if fmow_category in [30, 48]:
#             label[0] = 1
#         else:
#             label[0] = 0 
        # Train harder on 20 categories
        label[0] = self.params['fmow_class_names_mini'].index(bb['category'])
            
        if self.transform:
            sample = self.transform({'image': image, 'label':label})
            
        return sample['image'], sample['label']
    
class ToTensor(object):
    """Convert ndarrays to Tensors."""

    def __call__(self, sample):
        image, label = sample['image'], sample['label']
        # Move color channel
        image = image.transpose((2, 0, 1))
        return {'image': torch.FloatTensor(image), 'label': torch.LongTensor(label)}
    
class Rescale(object):
    """Rescale the image in a sample to a given size.

    Args:
        output_size (tuple): Desired output size. Output is
            matched to output_size
    """

    def __init__(self, output_size):
        assert isinstance(output_size, (tuple))
        self.output_size = output_size

    def __call__(self, sample):
        image, label = sample['image'], sample['label']
        h, w = image.shape[:2]
        new_h, new_w = self.output_size
        new_h, new_w = int(new_h), int(new_w)
        image = cv2.resize(image, (new_w, new_h))
        image = image[:,:,np.newaxis]
        return {'image': image, 'label':label}

class Normalize(object):
    """Rescale the image in a sample to a given size.

    Args:
        output_size (tuple): Desired output size. Output is
            matched to output_size
    """

    def __init__(self, mean, std):
        self.mean = mean
        self.std = std

    def __call__(self, sample):
        image, label = sample['image'], sample['label']
        mean_image = np.ones(image.shape)*self.mean
        image = (image - mean_image) / self.std
        return {'image': image, 'label':label}

    
    
    
class FMOWDataset_test(Dataset):
    """Functional Map of World Dataset"""

    def __init__(self, params, transform=None):
        """
        Args:
            params (dict): Dict containing key parameters of the project
            transform (callable, optional): Optional transform to be applied
                on a sample.
        """
        self.params = params
        self.transform = transform
        self.map = {}
        self.curr_index = 0
        path = os.path.join(params['dataset'], 'test')
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith('_rgb.jpg'):
                    image_p = os.path.join(root, file)
                    if not os.path.isfile(image_p):
                            continue
                    metadata_p = image_p[:-3] + 'json'
                    try:
                        m = open(metadata_p)
                        metadata = json.load(m)
                        m.close()
                    except Exception as e:
                        print("Exception: %s" % e)
                    if not isinstance(metadata['bounding_boxes'], list):
                        metadata['bounding_boxes'] = [metadata['bounding_boxes']]
                    for i, bb in enumerate(metadata['bounding_boxes']):
                        self.map[self.curr_index] = image_p + ":" + str(i)
                        self.curr_index += 1

    def __len__(self):
        return len(self.map)

    def __getitem__(self, idx):
        image_p, box_index = self.map[idx].split(":")
        box_index = int(box_index)
        metadata_p = image_p[:-3] + 'json'
        try:
            image = cv2.imread(image_p, 0).astype(np.float32)
            m = open(metadata_p)
            metadata = json.load(m)
            m.close()
        except Exception as e:
            print("Exception: %s" % e)
        if not isinstance(metadata['bounding_boxes'], list):
            metadata['bounding_boxes'] = [metadata['bounding_boxes']]
        # Locate the correct bounding box in the image
        bb = metadata['bounding_boxes'][box_index]
        
        box = bb['box']
        buffer = 16
        r1 = box[1] - buffer
        r2 = box[1] + box[3] + buffer
        c1 = box[0] - buffer
        c2 = box[0] + box[2] + buffer
        r1 = max(r1, 0)
        r2 = min(r2, image.shape[0])
        c1 = max(c1, 0)
        c2 = min(c2, image.shape[1])
        image = image[r1:r2, c1:c2, np.newaxis]
        
        label = np.ndarray([1,])
#         fmow_category = self.params['fmow_class_names'].index(bb['category'])         
#         if fmow_category in [30, 48]:
#             label[0] = 1
#         else:
#             label[0] = 0 
        # Train harder on 20 categories
        label[0] = self.params['fmow_class_names_mini'].index(bb['category'])  
            
        if self.transform:
            sample = self.transform({'image': image, 'label':label})
            
        return sample['image'], sample['label']
    
    
