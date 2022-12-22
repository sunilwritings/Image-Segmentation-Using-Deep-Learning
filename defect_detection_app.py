# -*- coding: utf-8 -*-
"""Defect_Detection_app.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1qsmtaskdF3bh_7660-IYGIzC5GuQgqjc
"""

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import os
import pickle
import matplotlib.patches as patches
import re
import random
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.python.keras.utils import generic_utils
from tensorflow.keras import utils
from tensorflow.keras import models
from tensorflow.keras.utils import plot_model
from tensorflow.keras.utils import get_custom_objects
from PIL import Image
from tensorflow.keras import backend as K
from tensorflow.keras.models import Model,load_model
from tensorflow.keras.regularizers import l2
import os
os.environ["SM_FRAMEWORK"] = "tf.keras"
import segmentation_models as sm
sm.set_framework('tf.keras')
from segmentation_models import get_preprocessing
import streamlit as st


st.title("Welcome To AI Based Steel Surface Defects Detector")
image = Image.open('steel.jpg')
st.image(image, caption='Steel Surface')

st.text('This app will segment the defect existed in steel surfaces')
st.text('You can upload the data below :')

col1= st.columns(1)
data = st.file_uploader('Upload the csv file below',type=['csv'])

col1 = st.columns(1)
predict_button = st.button('Predict on uploaded files')



#https://www.kaggle.com/paulorzp/rle-functions-run-lenght-encode-decode
def rle_to_mask(rle):
# CONVERT RLE TO MASK
   if (pd.isnull(rle))|(rle=='')|(rle=='-1'):
       return np.zeros((256,800),dtype=np.uint8) #If the EncodedPixels string is empty an empty mask is returned
   height=256
   width=1600
   mask=np.zeros(width*height,dtype=np.uint8)
   array=np.asarray([int(x) for x in rle.split()])
   starts=array[0::2]-1
   lengths=array[1::2]
   for index,start in enumerate(starts):
      mask[int(start):int(start+lengths[index])]=1
   return mask.reshape((height,width),order='F')[::,::2]


class train_DataGenerator(tf.keras.utils.Sequence):
    def __init__(self,dataframe,batch_size=1,shuffle=True,preprocess=None,info={}):
     self.batch_size = batch_size
     self.df = dataframe
     self.indices = self.df.index.tolist()
     self.preprocess = preprocess
     self.shuffle = shuffle
     self.on_epoch_end()
    def __len__(self):
     return len(self.indices) // (self.batch_size)
    def __getitem__(self, index):
     index = self.index[index * self.batch_size:(index + 1) * self.batch_size]
     batch = [self.indices[k] for k in index]
     X, y = self.__get_data(batch)
     return X, y
    def on_epoch_end(self):
     self.index = np.arange(len(self.indices))
     if self.shuffle == True:
        np.random.shuffle(self.index)
    def __get_data(self, batch):
     train_datagen = ImageDataGenerator()
#https://www.geeksforgeeks.org/python-select-random-value-from-a-list/
     X=np.empty((self.batch_size,256,800,3),dtype=np.float32) # image place-holders
     Y=np.empty((self.batch_size,256,800,1),dtype=np.float32)# 1 mask place-holders
     for i,id in enumerate(batch):
      path=os.path.join(os.getcwd(),'Defect/')
      X[i,] = Image.open(path + str(self.df['image_id'].loc[id])).resize((800,256))
      Y[i,:,:,0]=rle_to_mask(self.df['rle'].loc[id])
      t=random.choice([0,10,20,30,40])
      z=random.choice([0.8,1])
      flip=random.choice(['True','False'])
      param={'tx':t,'ty':t,'zx':z,'zy':z,}
      for i,e in enumerate(X):
          X[i] = train_datagen.apply_transform(e,transform_parameters=param)
      for i,f in enumerate(Y):
          Y[i] = train_datagen.apply_transform(f,transform_parameters=param)
      if self.preprocess!=None: X = self.preprocess(X)
      return X,Y


# Implementing custom data generator
#https://towardsdatascience.com/implementing-custom-data-generators-in-keras-de56f013581c
class test_DataGenerator(tf.keras.utils.Sequence):
  def __init__(self,dataframe,batch_size=1,shuffle=False,preprocess=None,info={}):
   self.batch_size = batch_size
   self.df = dataframe
   self.indices = self.df.index.tolist()
   self.preprocess = preprocess
   self.shuffle = shuffle
   self.on_epoch_end()
  def __len__(self):
   return len(self.indices) // (self.batch_size)
  def __getitem__(self, index):
   index = self.index[index * self.batch_size:(index + 1) * self.batch_size]
   batch = [self.indices[k] for k in index]
   X, y = self.__get_data(batch)
   return X, y
  def on_epoch_end(self):
   self.index = np.arange(len(self.indices))
   if self.shuffle == True:
     np.random.shuffle(self.index)
  def __get_data(self, batch):
   X = np.empty((self.batch_size,256,800,3),dtype=np.float32) # image place-holders
   Y = np.empty((self.batch_size,256,800,1),dtype=np.float32)# 1 mask place-holders
   for i, id in enumerate(batch):
     path=os.path.join(os.getcwd(),'Defect/')
     X[i,] = Image.open(path+ str(self.df['image_id'].loc[id])).resize((800,256))
     Y[i,:,:,0]=rle_to_mask(self.df['rle'].loc[id])
    # preprocess input
   if self.preprocess!=None: X = self.preprocess(X)
   return X,Y

def rle2mask(rle):
# CONVERT RLE TO MASK
   if (pd.isnull(rle))|(rle=='')|(rle=='-1'):
      return np.zeros((256,1600) ,dtype=np.uint8)
   height= 256
   width = 1600
   mask= np.zeros( width*height ,dtype=np.uint8)
   array = np.asarray([int(x) for x in rle.split()])
   starts = array[0::2]-1
   lengths = array[1::2]
   for index, start in enumerate(starts):
      mask[int(start):int(start+lengths[index])] = 1
   return mask.reshape( (height,width), order='F' )



def plot_mask(rle_defect,k,pred):
   
     path=os.path.join(os.getcwd(),'Defect/')
     # Create figure and axes
     fig,ax=plt.subplots(1,3,figsize=(15,2))
     fig.suptitle('Defect_image')
   
     image_id=rle_defect[0][0]
     rle=rle_defect[0][1]
     im=Image.open(path+str(image_id))
     ax[0].imshow(im)
     ax[0].set_title(image_id)
     mask=rle2mask(rle)
     ax[1].imshow(mask)
     ax[1].set_title("Actual Mask for "+str(image_id))
     c1=Image.fromarray(pred[0][:,:,0])
     ax[2].imshow(np.array(c1.resize((1600,256)))>0.5)
     ax[2].set_title("Predicted Mask for "+str(image_id))
     fig.set_facecolor("yellow")
     st.pyplot(fig)

#st.cache
def get_model():
    UNet=tf.keras.models.load_model('model_unet.h5',custom_objects={'binary_crossentropy_plus_dice_loss':sm.losses.bce_dice_loss,'iou_score':iou_score})
    return UNet

def prediction(data):
    state = st.text('\n Please wait while the model predict the defect in image.....')
    progress_bar = st.progress(0)
    start = time.time()
    model = get_model()
    train_preds=model.predict_generator(test_DataGenerator(data[1:2],preprocess=get_preprocessing('mobilenet')),verbose=1)
    plot_mask(data[1:2].values,4,train_preds)

    progress_bar.progress(100)
    st.write('Time taken for prediction :', str(round(end-start,3))+' seconds')
    progress_bar.empty()
    state.text('\n Completed!')

if predict_button:
    if data is not None:
        df = pd.read_csv(data)
        st.text('Uploaded Data :')
        st.dataframe(df)
        prediction(df)  

if __name__ == "__main__":
    main()
