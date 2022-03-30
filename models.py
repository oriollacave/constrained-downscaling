import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

#torch.set_default_dtype(torch.float64)
#building blocks for networks
def conv3x3(in_channels, out_channels, stride=1):
    return nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)

class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1, downsample=None):
        super(ResidualBlock, self).__init__()
        self.conv1 = conv3x3(in_channels, out_channels, stride)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(out_channels, out_channels)
        
    def forward(self, x):
        residual = x
        out = self.conv1(x)
        out = self.relu(out)
        out = self.conv2(out)
        out += residual
        out = self.relu(out)
        return out

class DownscaleConstraints(nn.Module):
    def __init__(self, upsampling_factor):
        super(DownscaleConstraints, self).__init__()
        self.pool = torch.nn.AvgPool2d(kernel_size=upsampling_factor)
        self.upsampling_factor = upsampling_factor
    def forward(self, y, lr):
        sum_y = self.pool(y)
        out = y*torch.kron(lr*1/sum_y, torch.ones((self.upsampling_factor,self.upsampling_factor)).to('cuda'))
        return out
    
    
class AddDownscaleConstraints(nn.Module):
    def __init__(self, upsampling_factor):
        super(AddDownscaleConstraints, self).__init__()
        self.pool = torch.nn.AvgPool2d(kernel_size=upsampling_factor)
        self.upsampling_factor = upsampling_factor
    def forward(self, y, lr):
        sum_y = self.pool(y)
        out =y+ torch.kron(lr-sum_y, torch.ones((self.upsampling_factor,self.upsampling_factor)).to('cuda'))
        return out
    
    
class SoftmaxConstraints(nn.Module):
    def __init__(self, upsampling_factor, exp_factor=1):
        super(SoftmaxConstraints, self).__init__()
        self.pool = torch.nn.AvgPool2d(kernel_size=upsampling_factor)
        self.upsampling_factor = upsampling_factor
        self.exp_factor = exp_factor
    def forward(self, y, lr):
        y = torch.exp(self.exp_factor*y)
        sum_y = self.pool(y)
        out = y*torch.kron(lr*1/sum_y, torch.ones((self.upsampling_factor,self.upsampling_factor)).to('cuda'))
        return out
    
class MRSoftmaxConstraints(nn.Module):
    def __init__(self, upsampling_factor, exp_factor=1):
        super(MRSoftmaxConstraints, self).__init__()
        self.pool = torch.nn.AvgPool2d(kernel_size=int(upsampling_factor/2))
        self.upsampling_factor = int(upsampling_factor/2)
        self.exp_factor = exp_factor
    def forward(self, y, mr):
        y = torch.exp(self.exp_factor*y)
        sum_y = self.pool(y)
        out = y*torch.kron(mr*1/sum_y, torch.ones((self.upsampling_factor,self.upsampling_factor)).to('cuda'))
        return out
    


    
#network architecture
class ResNet1(nn.Module):
    def __init__(self, number_channels=64, number_residual_blocks=4, upsampling_factor=2, noise=False, downscale_constraints=False, softmax_constraints=False, dim=2):
        super(ResNet1, self).__init__()
        # First layer
        if noise:
            self.conv_trans0 = nn.ConvTranspose2d(100, 1, kernel_size=(32,32), padding=0, stride=1)
            self.conv1 = nn.Sequential(nn.Conv2d(2, number_channels, kernel_size=3, stride=1, padding=1), nn.ReLU(inplace=True))
        else:
            self.conv1 = nn.Sequential(nn.Conv2d(dim, number_channels, kernel_size=3, stride=1, padding=1), nn.ReLU(inplace=True))
        #Residual Blocks
        self.res_blocks = nn.ModuleList()
        for k in range(number_residual_blocks):
            self.res_blocks.append(ResidualBlock(number_channels, number_channels))
        # Second conv layer post residual blocks
        self.conv2 = nn.Sequential(
            nn.Conv2d(number_channels, number_channels, kernel_size=1, stride=1, padding=0), nn.ReLU(inplace=True))
        # Upsampling layers
        self.upsampling = nn.ModuleList()
        for k in range(int(np.rint(np.log2(upsampling_factor)))):
            self.upsampling.append(nn.ConvTranspose2d(number_channels, number_channels, kernel_size=2, padding=0, stride=2) )
        # Next layer after upper sampling
        self.conv3 = nn.Sequential(nn.Conv2d(number_channels, number_channels, kernel_size=1, stride=1, padding=0), nn.ReLU(inplace=True))
        # Final output layer
        self.conv4 = nn.Conv2d(number_channels, dim, kernel_size=1, stride=1, padding=0)      
        #optional renomralization layer
        if downscale_constraints:
            if softmax_constraints:
                self.downscale_constraint = SoftmaxConstraints(upsampling_factor=upsampling_factor)
            else:
                self.downscale_constraint = DownscaleConstraints(upsampling_factor=upsampling_factor)
            
        self.noise = noise
        self.downscale_constraints = downscale_constraints
    def forward(self, x, z=None): 
        if self.noise:
            out = self.conv_trans0(z)
            out = self.conv1(torch.cat((x,out), dim=1))
            for layer in self.res_blocks:
                out = layer(out)
            out = self.conv2(out)
            for layer in self.upsampling:
                out = layer(out)
            out = self.conv3(out)
            out = self.conv4(out)
            if self.downscale_constraints:
                out = self.downscale_constraint(out, x)
            return out  
        else:
            
            out = self.conv1(x)
            for layer in self.res_blocks:
                out = layer(out)
            out = self.conv2(out)
            for layer in self.upsampling:
                out = layer(out)
            out = self.conv3(out)
            out = self.conv4(out)
            if self.downscale_constraints:
                out = self.downscale_constraint(out, x)
            return out  
        
        
class ResNet2(nn.Module):
    def __init__(self, number_channels=64, number_residual_blocks=4, upsampling_factor=2, noise=False, downscale_constraints=False, softmax_constraints=False, dim=1):
        super(ResNet2, self).__init__()
        # First layer
        if noise:
            self.conv_trans0 = nn.ConvTranspose2d(100, 1, kernel_size=(32,32), padding=0, stride=1)
            self.conv1 = nn.Sequential(nn.Conv2d(dim, number_channels, kernel_size=3, stride=1, padding=1), nn.ReLU(inplace=True))
        else:
            self.conv1 = nn.Sequential(nn.Conv2d(dim, number_channels, kernel_size=3, stride=1, padding=1), nn.ReLU(inplace=True))
        #Residual Blocks
        self.res_blocks = nn.ModuleList()
        for k in range(number_residual_blocks):
            self.res_blocks.append(ResidualBlock(number_channels, number_channels))
        # Second conv layer post residual blocks
        self.conv2 = nn.Sequential(
            nn.Conv2d(number_channels, number_channels, kernel_size=1, stride=1, padding=0), nn.ReLU(inplace=True))
        # Upsampling layers
        self.upsampling = nn.ModuleList()
        for k in range(int(np.rint(np.log2(upsampling_factor)))):
            self.upsampling.append(nn.ConvTranspose2d(number_channels, number_channels, kernel_size=2, padding=0, stride=2) )
        # Next layer after upper sampling
        self.conv3 = nn.Sequential(nn.Conv2d(number_channels, number_channels, kernel_size=1, stride=1, padding=0), nn.ReLU(inplace=True))
        # Final output layer
        self.conv4 = nn.Conv2d(number_channels, dim, kernel_size=1, stride=1, padding=0)      
        #optional renomralization layer
        if downscale_constraints:
            if softmax_constraints:
                self.downscale_constraint = SoftmaxConstraints(upsampling_factor=upsampling_factor)
            else:
                self.downscale_constraint = DownscaleConstraints(upsampling_factor=upsampling_factor)
            
        self.noise = noise
        self.downscale_constraints = downscale_constraints
    def forward(self, x, mr, z=None): 
        if self.noise:
            out = self.conv_trans0(z)
            out = self.conv1(torch.cat((x,out), dim=1))
            for layer in self.res_blocks:
                out = layer(out)
            out = self.conv2(out)
            for layer in self.upsampling:
                out = layer(out)
            out = self.conv3(out)
            out = self.conv4(out)
            if self.downscale_constraints:
                out = self.downscale_constraint(out, x)
            return out  
        else:
            
            out = self.conv1(x)
            for layer in self.upsampling:
                out = layer(out)
            out = self.conv2(out)    
            for layer in self.res_blocks:
                out = layer(out)
            out = self.conv3(out)
            out = self.conv4(out)
            if self.downscale_constraints:
                out = self.downscale_constraint(out, mr)
            #out[:,0,:,:] *= 16
            return out  
        
class MRResNet(nn.Module):
    def __init__(self, number_channels=64, number_residual_blocks=4, upsampling_factor=2, noise=False, downscale_constraints=False, softmax_constraints=False, dim=1):
        super(MRResNet, self).__init__()
        # First layer
        if noise:
            self.conv_trans0 = nn.ConvTranspose2d(100, 1, kernel_size=(32,32), padding=0, stride=1)
            self.conv1 = nn.Sequential(nn.Conv2d(dim, number_channels, kernel_size=3, stride=1, padding=1), nn.ReLU(inplace=True))
        else:
            self.conv1 = nn.Sequential(nn.Conv2d(dim, number_channels, kernel_size=3, stride=1, padding=1), nn.ReLU(inplace=True))
        #Residual Blocks
        self.res_blocks1 = nn.ModuleList()
        for k in range(number_residual_blocks):
            self.res_blocks1.append(ResidualBlock(number_channels, number_channels))
        self.res_blocks2 = nn.ModuleList()
        for k in range(number_residual_blocks):
            self.res_blocks2.append(ResidualBlock(number_channels, number_channels))
        # Second conv layer post residual blocks
        self.conv2 = nn.Sequential(
            nn.Conv2d(number_channels,1, kernel_size=1, stride=1, padding=0), nn.ReLU(inplace=True))
        # Upsampling layers
        self.upsampling1 = nn.ConvTranspose2d(number_channels, number_channels, kernel_size=2, padding=0, stride=2) 
        self.upsampling2 = nn.ConvTranspose2d(number_channels, number_channels, kernel_size=2, padding=0, stride=2) 
        
        # Next layer after upper sampling
        self.conv3 = nn.Sequential(nn.Conv2d(1, number_channels, kernel_size=1, stride=1, padding=0), nn.ReLU(inplace=True))
        # Final output layer
        self.conv4 = nn.Conv2d(number_channels, dim, kernel_size=1, stride=1, padding=0)      
        #optional renomralization layer
        self.downscale_constraint1 = SoftmaxConstraints(upsampling_factor=int(upsampling_factor/2))
        self.downscale_constraint2 = SoftmaxConstraints(upsampling_factor=int(upsampling_factor/2))
        
            
        self.noise = noise
        
    def forward(self, x): 
        out = self.conv1(x)
        out = self.upsampling1(out)
        for layer in self.res_blocks1:
            out = layer(out) 
        out = self.conv2(out)
        mr = self.downscale_constraint1(out, x)
        out = self.conv3(mr)
        out = self.upsampling2(out)
        for layer in self.res_blocks2:
            out = layer(out)
        out = self.conv4(out)
        out = self.downscale_constraint2(out, mr)
        return out 
          
class ResNetNoise(nn.Module):
    def __init__(self, number_channels=64, number_residual_blocks=4, upsampling_factor=2, noise=False, downscale_constraints=False, softmax_constraints=False, dim=1):
        super(ResNetNoise, self).__init__()
        # First layer
        
        self.linear = nn.Linear(100, 32*32)
        self.conv1 = nn.Sequential(nn.Conv2d(2, number_channels, kernel_size=3, stride=1, padding=1), nn.ReLU(inplace=True))
        
        #Residual Blocks
        self.res_blocks = nn.ModuleList()
        for k in range(number_residual_blocks):
            self.res_blocks.append(ResidualBlock(number_channels, number_channels))
        # Second conv layer post residual blocks
        self.conv2 = nn.Sequential(
            nn.Conv2d(number_channels, number_channels, kernel_size=1, stride=1, padding=0), nn.ReLU(inplace=True))
        # Upsampling layers
        self.upsampling = nn.ModuleList()
        for k in range(int(np.rint(np.log2(upsampling_factor)))):
            self.upsampling.append(nn.ConvTranspose2d(number_channels, number_channels, kernel_size=2, padding=0, stride=2) )
        # Next layer after upper sampling
        self.conv3 = nn.Sequential(nn.Conv2d(number_channels, number_channels, kernel_size=1, stride=1, padding=0), nn.ReLU(inplace=True))
        # Final output layer
        self.conv4 = nn.Conv2d(number_channels, dim, kernel_size=1, stride=1, padding=0)      
        #optional renomralization layer
        if downscale_constraints:
            if softmax_constraints:
                self.downscale_constraint = SoftmaxConstraints(upsampling_factor=upsampling_factor)
            else:
                self.downscale_constraint = DownscaleConstraints(upsampling_factor=upsampling_factor)
            
        self.noise = noise
        self.downscale_constraints = downscale_constraints
    def forward(self, x, z): 
        out = self.linear(z)
        out = torch.reshape(out, (x.shape))
        out = self.conv1(torch.cat((x,out), dim=1))
        
        
        for layer in self.upsampling:
            out = layer(out)
        out = self.conv2(out)    
        for layer in self.res_blocks:
            out = layer(out)
        out = self.conv3(out)
        out = self.conv4(out)
        if self.downscale_constraints:
            out = self.downscale_constraint(out, x)
        return out  
       
                    
class Discriminator(nn.Module):
    def __init__(self):
        super(Discriminator, self).__init__()
        self.conv1 = nn.Sequential(nn.Conv2d(1, 32, 3, stride=1, padding=1), nn.ReLU(inplace=True))
        self.conv2 = nn.Sequential(nn.Conv2d(32, 32, 3, stride=2, padding=1), nn.ReLU(inplace=True))
        self.conv3 = nn.Sequential(nn.Conv2d(32, 64, 3, stride=2, padding=1), nn.ReLU(inplace=True))
        self.conv4 = nn.Sequential(nn.Conv2d(64, 64, 3, stride=2, padding=1), nn.ReLU(inplace=True)) 
        self.conv5 = nn.Sequential(nn.Conv2d(64, 128, 3, stride=2, padding=1), nn.ReLU(inplace=True))
        self.conv6 = nn.Sequential(nn.Conv2d(128, 128, 3, stride=2, padding=1), nn.ReLU(inplace=True)) 
        self.conv9 = nn.Conv2d(128, 1, 1, stride=1, padding=1)

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)    
        x = self.conv3(x)
        x = self.conv4(x)
        x = self.conv5(x)
        x = self.conv6(x)
        x = self.conv9(x)
        return torch.sigmoid(F.avg_pool2d(x, x.size()[2:])).view(x.size()[0], -1)
    
####time-series model
###work in progress
### data shape (batch_size, time_steps=8, channels=1, H, W)


class TimeDistributed(nn.Module):
    def __init__(self, module, batch_first=True):
        super(TimeDistributed, self).__init__()
        self.module = module
        self.batch_first = batch_first

    def forward(self, x):
        if len(x.size()) <= 2:
            return self.module(x)
        # Squash samples and timesteps into a single axis
        shape = x.shape
        x_reshape = x.reshape(shape[0]*shape[1], shape[2],shape[3], shape[4])  # (samples * timesteps, input_size)
        y = self.module(x_reshape)
        # We have to reshape Y
        y = y.reshape(shape[0],shape[1],y.shape[1],y.shape[2],y.shape[3])
        return y


class GenGate(nn.Module):
    def __init__(self, activation='sigmoid', number_of_inchannels=64, number_of_outchannels=64):
        super(GenGate, self).__init__()
        self.refl = nn.ReflectionPad2d(1)
        self.conv = nn.Conv2d(number_of_inchannels, number_of_outchannels, kernel_size=(3,3))
        if activation is not None:
            self.act = nn.Sigmoid()
        else:
            self.act = None
               
    def forward(self, x):
        x = self.refl(x)
        x = self.conv(x)
        if self.act is not None:
            x = self.act(x)
        return x
            
            
class GenGateGRU(nn.Module):
    def __init__(self, return_sequences=True, time_steps=8):
        super(GenGateGRU, self).__init__()
        self.update_gate = GenGate('sigmoid', 128,64)
        self.reset_gate = GenGate('sigmoid', 128,64)
        self.output_gate = GenGate(None, 128,64)
        self.return_sequences = return_sequences
        self.time_steps = time_steps

    def forward(self, inputs):
        (xt,h) = inputs
        h_all = []
        for t in range(self.time_steps):
            x = xt[:,t,...]
            xh = torch.cat((x,h), dim=1)
            z = self.update_gate(xh)
            r = self.reset_gate(xh)
            o = self.output_gate(torch.cat((x,r*h), dim=1))
            h = z*h + (1-z)*torch.tanh(o)
            if self.return_sequences:
                h_all.append(h)
        return torch.stack(h_all,dim=1) if self.return_sequences else h

                

class ResidualBlockRNN(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1, activation='leaky_relu'):
        super(ResidualBlockRNN, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False, padding_mode='reflect')
        if activation == 'relu':
            self.relu1 = nn.ReLU(inplace=True)
        elif activation == 'leaky_relu':
            self.relu1 = nn.LeakyReLU(inplace=True)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False, padding_mode='reflect')
        if activation == 'relu':
            self.relu2 = nn.ReLU(inplace=True)
        elif activation == 'leaky_relu':
            self.relu2 = nn.LeakyReLU(inplace=True)
        
    def forward(self, x):
        residual = x
        out = self.relu1(x)
        out = TimeDistributed(self.conv1)(x)
        out = self.relu2(out)
        out = TimeDistributed(self.conv2)(out)
        out += residual
        return out
        
class ResidualBlockRNNSpectral(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1, activation='leaky_relu'):
        super(ResidualBlockRNNSpectral, self).__init__()
        self.conv1 = nn.utils.spectral_norm(nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False, padding_mode='reflect'))
        if activation == 'relu':
            self.relu1 = nn.ReLU(inplace=True)
        elif activation == 'leaky_relu':
            self.relu1 = nn.LeakyReLU(inplace=True)
        self.conv2 = nn.utils.spectral_norm(nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False, padding_mode='reflect'))
        if activation == 'relu':
            self.relu2 = nn.ReLU(inplace=True)
        elif activation == 'leaky_relu':
            self.relu2 = nn.LeakyReLU(inplace=True)
        
    def forward(self, x):
        residual = x
        out = self.relu1(out)
        out = TimeDistributed(self.conv1)(x)
        out = self.relu2(out)
        out = TimeDistributed(self.conv2)(out)
        out += residual
        return out
        
class ResidualBlockN(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1, activation='leaky_relu'):
        super(ResidualBlockN, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False, padding_mode='reflect')
        if activation == 'relu':
            self.relu1 = nn.ReLU(inplace=True)
        elif activation == 'leaky_relu':
            self.relu1 = nn.LeakyReLU(inplace=True)
        self.conv2 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False, padding_mode='reflect')
        if activation == 'relu':
            self.relu2 = nn.ReLU(inplace=True)
        elif activation == 'leaky_relu':
            self.relu2 = nn.LeakyReLU(inplace=True)
        
    def forward(self, x):
        residual = x
        out = self.relu1(x)
        out = self.conv1(out)
        out = self.relu2(out)
        out = self.conv2(out)
        out += residual
        return out
        
class InitialState(nn.Module):
    def __init__(self, number_channels=256, number_residual_blocks=3):
        super(InitialState, self).__init__()
        self.reflpadd = nn.ReflectionPad2d(1)
        self.conv = nn.Conv2d(1, number_channels-8, kernel_size=(3,3))
        self.res_blocks = nn.ModuleList()
        for k in range(number_residual_blocks):
            self.res_blocks.append(ResidualBlockN(number_channels, number_channels, stride=1, activation='relu'))
        
    def forward(self, x, noise):
        out = self.reflpadd(x)
        out = self.conv(out)
        out = torch.cat((out, noise))
        for layer in self.res_blocks:
            out = layer(out)
        return out
    
class InitialStateDet(nn.Module):
    def __init__(self, number_channels=64,  number_residual_blocks=3):
        super(InitialStateDet, self).__init__()
        self.reflpadd = nn.ReflectionPad2d(1)
        self.conv = nn.Conv2d(1, number_channels,kernel_size=(3,3), padding=1)
        self.res_blocks = nn.ModuleList()
        for k in range(number_residual_blocks):
            self.res_blocks.append(ResidualBlockN(number_channels, number_channels, stride=1, activation='relu'))
        
    def forward(self, x):
        #out = self.reflpadd(x)
        out = self.conv(x)
        for layer in self.res_blocks:
            out = layer(out)
        return out
        
class DicriminatorRNN(nn.Module):
    def __init__(self, number_channels=256, number_residual_blocks=3):
        super(Discriminator, self).__init__()
        block_channels = [128, 256]
        self.downsampling_hr = nn.ModuleList()
        self.downsampling_lr = nn.ModuleList()
        for (i,channels) in enumerate(block_channels):        
            self.downsampling_hr.append(ResidualBlockRNNSpectral(channels, channels, stride=2, activation='leaky_relu'))
            self.downsampling_lr.append(ResidualBlockRNNSpectral(channels, channels, stride=1, activation='leaky_relu'))
        self.res_blocks = nn.ModuleList()
        for k in range(number_residual_blocks):
            self.res_blocks.append(ResidualBlockRNNSpectral(number_channels, number_channels, stride=1, activation='leaky_relu'))
        self.res_blocks_hr = nn.ModuleList()
        for k in range(number_residual_blocks):
            self.res_blocks_hr.append(ResidualBlockRNNSpectral(number_channels, number_channels, stride=1, activation='leaky_relu'))
        self.conv_gru_lr = CustomGateGRU(update_gate=DiscGate(), reset_gate=DiscGate(), output_gate=DiscGate(activation=None), return_sequences=True, time_steps=8)
        self.conv_gru_hr = CustomGateGRU(update_gate=DiscGate(), reset_gate=DiscGate(), output_gate=DiscGate(activation=None), return_sequences=True, time_steps=8)
        avg_joint = TimeDistributed(nn.AveragePooling2D(kernel_size=(32,32)))
        avg_hr = TimeDistributed(nn.AveragePooling2D(kernel_size=(32,32)))
        sn_dense = TimeDistributed(nn.utils.spectral_norm(nn.Linear(512,256)))
        sn_dense_one = TimeDistributed(nn.utils.spectral_norm(nn.Linear(256,1) ))
        
    def forward(self, lr, hr):
        for layer in self.downsampling_hr:
            hr = layer(hr)
        for layer in self.downsampling_lr:
            lr = layer(lr)
        joint = torch.cat((lr, hr))
        for layer in self.res_blocks:
            joint = layer(joint)
        for layer in self.res_blocks_hr:
            hr = layer(hr)
        joint = self.conv_gru_joint([joint, torch.zeros_like(joint[:,0,...])])
        hr = self.conv_gru_hr([hr, torch.zeros_like(joint[:,0,...])])
        joint = avg_joint(joint)
        hr = avg_hr(hr)
        out = torch.cat((joint, hr))
        out = sn_dense(out)
        out = nn.LeakyReLU(out)
        out = sn_dense_one(out)
        return out     
            

class DiscGate(nn.Module):
    def __init__(self, activation='sigmoid'):
        super(DiscGate, self).__init__()
        self.refl = nn.ReflectionPad2d(1)
        self.conv = nn.utils.spectral_norm(nn.Conv2d(256, kernel_size=(3,3)))
        if activation is not None:
            self.act = nn.Sigmoid()
        else:
            self.act = None
               
    def forward(self, x):
        x = self.refl(x)
        x = self.conv(x)
        if self.act is not None:
            x = self.act(x)

    
class ConvGRUGenerator(nn.Module):    
    def __init__(self, number_channels=256, number_residual_blocks=3, upsampling_factor=2):
        super(ConvGRUGenerator, self).__init__()  
        self.initialize = InitialState()
        self.reflpadd1 = nn.ReflectionPad2d(1)
        self.conv1 = nn.Conv2d(1, number_channels-8, kernel_size=(3,3))
        self.res_blocks = nn.ModuleList()
        for k in range(number_residual_blocks):
            self.res_blocks.append(ResidualBlockRNN(number_channels, number_channels, stride=1, activation='relu'))
        self.convgru = GenGateGRU(update_gate=GenGate(), reset_gate=GenGate(), output_gate=GenGate(activation=None), return_sequences=True, time_steps=8)  
        self.upsampling = nn.ModuleList()
        block_channels = [256, 256, 128]
        for (i,channels) in enumerate(block_channels):
            if i > 0:
                self.upsampling.append(TimeDistributed(nn.UpsamplingBilinear2d(scale_factor=2)))
            self.upsampling.append(ResidualBlockRNN(channels, channels, stride=1, activation='leaky_relu'))          
        self.reflpadd2 = nn.ReflectionPad2d(1)
        self.conv2 = nn.Conv2d(number_channels, 1, kernel_size=(3,3)) 
    
    def forward(self, low_res, noise, initial_state_noise):   
        initial_state = self.initialize(low_reslow_res[:,0,...], initial_state_noise)
        xt = TimeDistributed(self.reflpadd1)(low_res)
        xt = TimeDistributed(self.conv1)(xt)
        xt = torch.cat((xt, noise))
        for layer in self.res_blocks:
            xt = layer(xt)
        x = self.convgru([xt, initial_state])
        h = x[:,-1,...]
        for layer in self.upsampling:
            x = layer(x)           
        x = TimeDistributed(self.reflpadd2)(x)
        img_out = TimeDistributed(self.conv2)(x)       
        return [img_out, h]
    
class ConvGRUGeneratorDet(nn.Module):    
    def __init__(self, number_channels=64, number_residual_blocks=3, upsampling_factor=2):
        super(ConvGRUGeneratorDet, self).__init__()  
        self.initialize = InitialStateDet()
        self.reflpadd1 = TimeDistributed(nn.ReflectionPad2d(1))
        self.conv1 = TimeDistributed(nn.Conv2d(1, number_channels, kernel_size=(3,3), padding=1))
        self.res_blocks = nn.ModuleList()
        for k in range(number_residual_blocks):
            self.res_blocks.append(ResidualBlockRNN(number_channels, number_channels, stride=1, activation='relu'))
        self.convgru = GenGateGRU(return_sequences=True, time_steps=8)  
        self.upsampling = nn.ModuleList()
        for i in range(3):
            if i > 0:
                self.upsampling.append(TimeDistributed(nn.UpsamplingBilinear2d(scale_factor=2)))
            self.upsampling.append(ResidualBlockRNN(number_channels, number_channels, stride=1, activation='leaky_relu'))          
        self.reflpadd2 = TimeDistributed(nn.ReflectionPad2d(1))
        self.conv2 = TimeDistributed(nn.Conv2d(number_channels, 1, kernel_size=(3,3), padding=1))
    
    def forward(self, low_res):   
        initial_state = self.initialize(low_res[:,0,...])
        #xt = self.reflpadd1(low_res)
        
        xt = self.conv1(low_res)
        for layer in self.res_blocks:
            xt = layer(xt)
        x = self.convgru([xt, initial_state])
        h = x[:,-1,...]
        for layer in self.upsampling:
            x = layer(x)           
        #x = self.reflpadd2(x)
        img_out = self.conv2(x)   
        return img_out







