from torch.utils import data
from memory_profiler import profile
from torch.utils.data import DataLoader
import torchvision.transforms as transforms
import torchvision.datasets as dataset
import torch.nn.functional as fun
import matplotlib.pyplot as plt
import torch.nn as nn
import numpy as np
import torchvision
import torch
import time

@profile
def dataset_load(tr_batch_size, val_batch_size, val_split):
    
    #Download and prepare dataset chunks by DataLoader
    tic = time.time()
    print("Downloading dataset and preparing DataLoader")
    master_dataset = dataset.MNIST(root = './data', train = True, transform = transforms.ToTensor(), download = True )
    test_dataset = dataset.MNIST(root = './data', train = False, transform = transforms.ToTensor())
    
    #Train and validation data is split with specified ratio ratio
    train_dataset, val_dataset = data.random_split(master_dataset, (int(len(master_dataset)*(1.0-val_split)), int(len(master_dataset)*val_split)))
    
    #define dataloaders with defined batch size for training and validation
    train_loader = DataLoader(dataset = train_dataset, batch_size = tr_batch_size, shuffle = True)
    val_loader = DataLoader(dataset = val_dataset, batch_size = val_batch_size, shuffle = True)
    test_loader = DataLoader(dataset = test_dataset, batch_size = tr_batch_size, shuffle = False)
    toc = time.time()
    
    print("Finished preparing. Total time elasped: "+str(toc - tic)+" seconds")
    print("Memory profile for dataset_load(): ")
    
    return( train_loader, val_loader, test_loader)

class DeepNN(nn.Module):
    """
    Class defining the structure of Deep Neural Network model and layers characterstics
    """
    def __init__(self, input_dim, nh1, nh2, nh3, nh4, nh5, output_dim):
        
        super(DeepNN, self).__init__()
        
        #hyperparameter setting 
        self.input_dim = input_dim
        self.nh1, self.nh2, self.nh3, self.nh4, self.nh5, = nh1, nh2, nh3, nh4, nh5
        self.output_dim = output_dim
        #layer definition 
        self.input_layer = nn.Linear(self.input_dim, self.nh1)
        self.hlayer1 = nn.Linear(self.nh1, self.nh2)
        self.hlayer2 = nn.Linear(self.nh2, self.nh3)
        self.hlayer3 = nn.Linear(self.nh3, self.nh4)
        self.hlayer4 = nn.Linear(self.nh4, self.nh5)
        self.output_layer = nn.Linear(self.nh5, self.output_dim)
        
    def forward(self, x):

        #propogation of each layer
        self.out1 = fun.softmax(self.input_layer(x))
        self.out2 = fun.softmax(self.hlayer1(self.out1))
        self.out3 = fun.softmax(self.hlayer2(self.out2))
        self.out4 = fun.softmax(self.hlayer3(self.out3))
        self.out5 = fun.softmax(self.hlayer4(self.out4))
        self.out6 = fun.softmax(self.output_layer(self.out5))
        
        return fun.softmax(self.out6, dim = 1)

    
def estimate_mutual_info(X, neurons, bins = 5):
    neuronal_MI = np.zeros(neurons.shape[1])
    index = 0
    for Y in neurons.T:
        sum = 0
        for dim in range(X.shape[1]):
            xy = np.histogram2d(X[:,dim], Y, bins)[0]
            x = np.histogram(X[:,dim], bins)[0]
            y = np.histogram(Y, bins)[0]
            ent_x = -1 * np.sum( x / np.sum(x) * np.log( x / np.sum(x)))
            ent_y = -1 * np.sum( y / np.sum(y) * np.log( y / np.sum(y)))
            ent_xy = -1 * np.sum( xy / np.sum(xy) * np.log( xy / np.sum(xy)))
            sum +=  ent_x + ent_y - ent_xy
        neuronal_MI[index] += sum
        index += 1
        print(sum)
    return(neuronal_MI)

#@profile
def pre_train_model(model, val_loader):
    
    layers = [model.input_layer, model.hlayer1, model.hlayer2, model.hlayer3, model.hlayer4]
    k_value = [10, 8, 5, 3, 2]
    
    for l_indx in range(len(layers)):
    
        print("Working on layer: "+str(l_indx))
        w_matrix = layers[l_indx].weight.data.clone().detach().numpy()
        b_matrix = layers[l_indx].bias.data.clone().detach().numpy()
        #load the input data X
        for _, (images, _) in enumerate(val_loader):

            images = images.reshape(-1, 28*28).clone().detach().numpy()
            activation = np.dot(images,w_matrix.T) + b_matrix 
            activation = 1/(1 + np.exp(-activation))
        tic_est = time.time()
        print("Estimation Information Theorotic quantities")
        neuronal_MI = estimate_mutual_info(images, activation)
        toc_est = time.time()
        print("Elasped time for estimation: "+str(round(toc_est-tic_est,1))+" seconds")
        # Get the index of sorted neurons based on MI value
        index_sorted = np.argsort(neuronal_MI)[::-1]
        #create clusters of given k value

        clusters = np.array_split(index_sorted, k_value[l_indx])
        bin_avg = []
        
        for i in clusters:
            bin_avg.append(np.sum(neuronal_MI[np.ix_(i)]) / neuronal_MI[np.ix_(i)].shape[0])
        
        while not stopping_criterion(iteration_count, clusters, bin_avg, neuronal_MI):    
            iteration_count = 0

            for bin in range(len(clusters)):
    
                step_size,  = calculate_step_size(clusters[bin]) 
                cost_function = calculate_cost_function(bin, clusters)
                w_matrix[np.ix_(clusters[bin])] -= step_size * cost_function
                b_matrix[np.ix_(clusters[bin])] -= step_size * cost_function
                iteration_count += 1

            activation = get_activation(l_indx, w_matrix, b_matrix)
            
        model.input_layer.weight.data = w_matrix
        model.input_layer.weight.data = b_matrix
    
    return(model)

if __name__ == '__main__':        

    tr_batch_size = 4800
    val_batch_size = 12000
    val_split = 0.2
    train_loader, val_loader, test_loader = dataset_load(tr_batch_size, val_batch_size, val_split)
    model = DeepNN(784, 1024, 120, 20, 20, 20, 10)
    print("Pretraining phase..")
    pre_trained_model = pre_train_model(model, val_loader)