"""This tutorial introduces the LeNet5 neural network architecture
using Theano.  LeNet5 is a convolutional neural network, good for
classifying images. This tutorial shows how to build the architecture,
and comes with all the hyper-parameters you need to reproduce the
paper's MNIST results.


This implementation simplifies the model in the following ways:

 - LeNetConvPool doesn't implement location-specific gain and bias parameters
 - LeNetConvPool doesn't implement pooling by average, it implements pooling
   by max.
 - Digit classification is implemented with a logistic regression rather than
   an RBF network
 - LeNet5 was not fully-connected convolutions at second layer

References:
 - Y. LeCun, L. Bottou, Y. Bengio and P. Haffner:
   Gradient-Based Learning Applied to Document
   Recognition, Proceedings of the IEEE, 86(11):2278-2324, November 1998.
   http://yann.lecun.com/exdb/publis/pdf/lecun-98.pdf

"""
import cPickle  # @UnusedImport
import gzip  # @UnusedImport
import os
import sys
import time
import numpy  # @NoMove
import theano  # @UnresolvedImport
import theano.tensor as T  # @UnresolvedImport
from theano.tensor.signal import downsample  # @UnresolvedImport
from theano.tensor.nnet import conv  # @UnresolvedImport
import scipy.io #for old .mat @UnresolvedImport
import h5py #for new .mat @UnresolvedImport
import getopt#parsing command line


from logistic_sgd import LogisticRegression, load_data
from mlp import HiddenLayer
from distutils import text_file


class LeNetConvPoolLayer(object):
    """Pool Layer of a convolutional network """

    def __init__(self, rng, input, filter_shape, image_shape, poolsize=(2, 2), Wi=None, bi=None):
        """
        Allocate a LeNetConvPoolLayer with shared variable internal parameters.

        :type rng: numpy.random.RandomState
        :param rng: a random number generator used to initialize weights

        :type input: theano.tensor.dtensor4
        :param input: symbolic image tensor, of shape image_shape

        :type filter_shape: tuple or list of length 4
        :param filter_shape: (number of filters, num input feature maps,
                              filter height,filter width)

        :type image_shape: tuple or list of length 4
        :param image_shape: (batch size, num input feature maps,
                             image height, image width)

        :type poolsize: tuple or list of length 2
        :param poolsize: the downsampling (pooling) factor (#rows,#cols)
        """

        assert image_shape[1] == filter_shape[1]
        self.input = input

        # there are "num input feature maps * filter height * filter width"
        # inputs to each hidden unit
        fan_in = numpy.prod(filter_shape[1:])
        # each unit in the lower layer receives a gradient from:
        # "num output feature maps * filter height * filter width" /
        #   pooling size
        fan_out = (filter_shape[0] * numpy.prod(filter_shape[2:]) /
                   numpy.prod(poolsize))
        # initialize weights with random weights
        W_bound = numpy.sqrt(6. / (fan_in + fan_out))



        if Wi is None:
            self.W = theano.shared(numpy.asarray(
            rng.uniform(low=-W_bound, high=W_bound, size=filter_shape),
            dtype=theano.config.floatX),
                               borrow=True)
        else:
            self.W = theano.shared(value=numpy.asarray(Wi, dtype=theano.config.floatX),name='W', borrow=True)

        if bi is None:
            # the bias is a 1D tensor -- one bias per output feature map
            b_values = numpy.zeros((filter_shape[0],), dtype=theano.config.floatX)
            self.b = theano.shared(value=b_values, borrow=True)
        else:
            b_values = numpy.asarray(bi, dtype=theano.config.floatX)
            self.b = theano.shared(value=b_values, borrow=True)

        # convolve input feature maps with filters
        conv_out = conv.conv2d(input=input, filters=self.W,
                filter_shape=filter_shape, image_shape=image_shape)

        # downsample each feature map individually, using maxpooling
        pooled_out = downsample.max_pool_2d(input=conv_out,
                                            ds=poolsize, ignore_border=True)

        # add the bias term. Since the bias is a vector (1D array), we first
        # reshape it to a tensor of shape (1,n_filters,1,1). Each bias will
        # thus be broadcasted across mini-batches and feature map
        # width & height
        self.output = T.tanh(pooled_out + self.b.dimshuffle('x', 0, 'x', 'x'))

        # store parameters of this layer
        self.params = [self.W, self.b]


def buildLayers(layer0_input,batch_size, dim, nkerns, rng,TT=None):
    # Construct the first convolutional pooling layer:
    # filtering reduces the image size to (28-5+1,28-5+1)=(24,24)
    # maxpooling reduces this further to (24/2,24/2) = (12,12)
    # 4D output tensor is thus of shape (batch_size,nkerns[0],12,12)

    W0 = None
    b0= None
    W1 = None
    b1= None
    W2 = None
    b2= None
    W3 = None
    b3= None
    W4 = None
    b4= None
    W5= None
    b5= None

    if TT != None:
        W0 = TT.Layer0_param.W.get_value(borrow=True)
        b0 = TT.Layer0_param.b.get_value(borrow=True)
        W1 = TT.Layer1_param.W.get_value(borrow=True)
        b1 = TT.Layer1_param.b.get_value(borrow=True)
        W2 = TT.Layer2_param.W.get_value(borrow=True)
        b2 = TT.Layer2_param.b.get_value(borrow=True)
        W3 = TT.Layer3_param.W.get_value(borrow=True)
        b3 = TT.Layer3_param.b.get_value(borrow=True)
        W4 = TT.Layer4_param.W.get_value(borrow=True)
        b4 = TT.Layer4_param.b.get_value(borrow=True)
        W5 = TT.Layer5_param.W.get_value(borrow=True)
        b5 = TT.Layer5_param.b.get_value(borrow=True)	

    layer0 = LeNetConvPoolLayer(rng, input=layer0_input,
            image_shape=(batch_size, dim, 128, 128),
            filter_shape=(nkerns[0], dim, 5, 5), poolsize=(2, 2),Wi=W0,bi=b0)

    # Construct the second convolutional pooling layer
    # filtering reduces the image size to (12-5+1,12-5+1)=(8,8)
    # maxpooling reduces this further to (8/2,8/2) = (4,4)
    # 4D output tensor is thus of shape (nkerns[0],nkerns[1],4,4)


    layer1 = LeNetConvPoolLayer(rng, input=layer0.output,
            image_shape=(batch_size, nkerns[0], 62, 62),
            filter_shape=(nkerns[1], nkerns[0], 5, 5), poolsize=(2, 2),Wi=W1,bi=b1)

    layer2 = LeNetConvPoolLayer(rng, input=layer1.output,
            image_shape=(batch_size, nkerns[1], 29, 29),
            filter_shape=(nkerns[2], nkerns[1], 6, 6), poolsize=(2, 2),Wi=W2,bi=b2)

	#output 12*12

    # the HiddenLayer being fully-connected, it operates on 2D matrices of
    # shape (batch_size,num_pixels) (i.e matrix of rasterized images).
    # This will generate a matrix of shape (20,32*4*4) = (20,512)
    layer3_input = layer2.output.flatten(2)

    # construct a fully-connected sigmoidal layer
    layer3 = HiddenLayer(rng, input=layer3_input, n_in=nkerns[2] * 12 * 12,
                         n_out=1024,Wi=W3,bi=b3)

    layer4 = HiddenLayer(rng, input=layer3.output, n_in=1024,
                         n_out=2048,Wi=W4,bi=b4)

    # classify the values of the fully-connected sigmoidal layer
    layer5 = HiddenLayer(rng, input=layer4.output, n_in=2048, n_out=51,Wi=W5,bi=b5)

    return [layer0, layer1, layer2, layer3, layer4, layer5];

def evaluate_lenet5(learning_rate=0.01, n_epochs=1,
                    pathDataset='path',
                    nameDataset='nameDataset',
                    nkerns=[32, 64, 64], batch_size=1, TT=None):
    """ Demonstrates lenet on MNIST dataset

    :type learning_rate: float
    :param learning_rate: learning rate used (factor for the stochastic
                          gradient)

    :type n_epochs: int
    :param n_epochs: maximal number of epochs to run the optimizer

    :type dataset: string
    :param dataset: path to the dataset used for training /testing (MNIST here)

    :type nkerns: list of ints
    :param nkerns: number of kernels on each layer
    """

    rng = numpy.random.RandomState(23455)

    #dim = 1;
    #datasets = load_data(dataset)


    # allocate symbolic variables for the data
    index = T.lscalar()  # index to a [mini]batch
    x = T.matrix('x')   # the data is presented as rasterized images
    y = T.matrix('y')  # the labels are presented as matrix
                        # [int] labels

    # useCustom = True;
    # if (useCustom):
    dim = 1;
    

    mat = h5py.File(pathDataset+'data_'+nameDataset+'.mat')  
    mat_result = h5py.File(pathDataset+'pose_'+nameDataset+'.mat')  
    x_train = numpy.transpose(numpy.asarray(mat['ftrain'],dtype=theano.config.floatX));  # @UndefinedVariable
    train_set_x =  theano.shared(x_train,borrow=False);
    x_validation = numpy.transpose(numpy.asarray(mat['fvalidation'],dtype=theano.config.floatX));
    valid_set_x =  theano.shared(x_validation,borrow=False);
    x_test = numpy.transpose(numpy.asarray(mat['ftest'],dtype=theano.config.floatX));
    test_set_x =  theano.shared(x_test,borrow=False);
    y_train = numpy.transpose(numpy.asarray(mat_result['rtrain'],dtype=theano.config.floatX));
    train_set_y = theano.shared(y_train,borrow=False);
    y_validation = numpy.transpose(numpy.asarray(mat_result['rvalidation'],dtype=theano.config.floatX));
    valid_set_y = theano.shared(y_validation,borrow=False);
    y_test = numpy.transpose(numpy.asarray(mat_result['rtest'],dtype=theano.config.floatX));
    test_set_y = theano.shared(y_test,borrow=False);
    
        #n_valid_batches = valid_set_x.shape[0]
        #n_test_batches = test_set_x.shape[0]
    # else:
    #     dim = 1;
    #     datasets = load_data(dataset)
    #     train_set_x, train_set_y = datasets[0]
    #     valid_set_x, valid_set_y = datasets[1]
    #     test_set_x, test_set_y = datasets[2]


    # datasets2 = load_data(dataset)
    # train_set_x2, train_set_y2 = datasets2[0]
    # valid_set_x2, valid_set_y2 = datasets2[1]
    # test_set_x2, test_set_y2 = datasets2[2]

    n_train_batches = train_set_x.get_value(borrow=True).shape[0]
    n_valid_batches = valid_set_x.get_value(borrow=True).shape[0]
    n_test_batches = test_set_x.get_value(borrow=True).shape[0]



    # compute number of minibatches for training, validation and testing

    n_train_batches /= batch_size
    n_valid_batches /= batch_size
    n_test_batches  /= batch_size



    #ishape = (28, 28)  # this is the size of MNIST images

    ######################
    # BUILD ACTUAL MODEL #
    ######################
    print ('... building the model')

    # Reshape matrix of rasterized images of shape (batch_size,28*28)
    # to a 4D tensor, compatible with our LeNetConvPoolLayer
    layer0_input = x.reshape((batch_size, dim, 128, 128))

    [ layer0, layer1, layer2, layer3, layer4, layer5] = buildLayers(layer0_input,batch_size, dim, nkerns,rng,TT);

    # the cost we minimize during training is the NLL of the model
    cost = layer5.point_error_rmse(y)

    # create a function to compute the mistakes that are made by the model
    test_model = theano.function([index], layer5.point_error_rmse(y),
             givens={
                x: test_set_x[index * batch_size: (index + 1) * batch_size],
                y: test_set_y[index * batch_size: (index + 1) * batch_size]})

    validate_model = theano.function([index], layer5.point_error_rmse(y),
            givens={
                x: valid_set_x[index * batch_size: (index + 1) * batch_size],
                y: valid_set_y[index * batch_size: (index + 1) * batch_size]})

    # create a list of all model parameters to be fit by gradient descent
    params = layer5.params + layer4.params + layer3.params + layer2.params + layer1.params + layer0.params

    # create a list of gradients for all model parameters
    grads = T.grad(cost, params)

    # train_model is a function that updates the model parameters by
    # SGD Since this model has many parameters, it would be tedious to
    # manually create an update rule for each model parameter. We thus
    # create the updates list by automatically looping over all
    # (params[i],grads[i]) pairs.
    updates = []
    for param_i, grad_i in zip(params, grads):
        updates.append((param_i, param_i - learning_rate * grad_i))

    train_model = theano.function([index], cost, updates=updates,
          givens={
            x: train_set_x[index * batch_size: (index + 1) * batch_size],
            y: train_set_y[index * batch_size: (index + 1) * batch_size]})

    model_prob = theano.function([index], layer5.pred,
             givens={
                x: test_set_x[index * batch_size: (index + 1) * batch_size]})
    result = theano.function([index], y,
             givens={
            y: test_set_y[index * batch_size: (index + 1) * batch_size]})

    # what you want: create a function to predict labels that are made by the model
   # model_predict = theano.function([index], layer4.y_pred,
   #          givens={
    #            x: test_set_x[index * batch_size: (index + 1) * batch_size]})

    ###############
    # TRAIN MODEL #
    ###############
    print ('... training')
    # early-stopping parameters
    patience = 10000  # look as this many examples regardless
    patience_increase = 2  # wait this much longer when a new best is
                           # found
    improvement_threshold = 0.995  # a relative improvement of this much is
                                   # considered significant
    validation_frequency = min(n_train_batches, patience / 2)
                                  # go through this many
                                  # minibatche before checking the network
                                  # on the validation set; in this case we
                                  # check every epoch

    best_params = None
    best_validation_loss = numpy.inf
    best_iter = 0
    test_score = 0.
    start_time = time.clock()

    epoch = 0
    done_looping = False

    while (epoch < n_epochs) and (not done_looping):
        epoch = epoch + 1
        for minibatch_index in xrange(n_train_batches):

            iter = (epoch - 1) * n_train_batches + minibatch_index

            if iter % 100 == 0:
                print ('training @ iter = '), iter
            cost_ij = train_model(minibatch_index)

            if (iter + 1) % validation_frequency == 0:

                # compute zero-one loss on validation set
                validation_losses = [validate_model(i) for i
                                     in xrange(n_valid_batches)]

                this_validation_loss = numpy.mean(validation_losses)
                print('epoch %i, minibatch %i/%i, validation error %f %%' % \
                      (epoch, minibatch_index + 1, n_train_batches, \
                       this_validation_loss ))

                # if we got the best validation score until now
                if this_validation_loss < best_validation_loss:

                    #improve patience if loss improvement is good enough
                    if this_validation_loss < best_validation_loss *  \
                       improvement_threshold:
                        patience = max(patience, iter * patience_increase)

                    # save best validation score and iteration number
                    best_validation_loss = this_validation_loss
                    best_iter = iter

                    print ([model_prob(i) for i in xrange(n_test_batches)])
                    #print [model_predict(i) for i in xrange(n_test_batches)]
                    #pathDataset+'data_'+ nameDataset+'.mat'
                    save_file = open('result_'+nameDataset+'.dat', 'wb') # this will overwrite current contents
                    cPickle.dump(layer0, save_file, protocol=cPickle.HIGHEST_PROTOCOL)
                    cPickle.dump(layer1, save_file, protocol=cPickle.HIGHEST_PROTOCOL)
                    cPickle.dump(layer2, save_file, protocol=cPickle.HIGHEST_PROTOCOL)
                    cPickle.dump(layer3, save_file, protocol=cPickle.HIGHEST_PROTOCOL)
                    cPickle.dump(layer4, save_file, protocol=cPickle.HIGHEST_PROTOCOL)
                    cPickle.dump(layer5, save_file, protocol=cPickle.HIGHEST_PROTOCOL)
                    save_file.close()


                    # test it on the test set
                    test_losses = [test_model(i) for i in xrange(n_test_batches)]
                    test_score = numpy.mean(test_losses)
                    print(('     epoch %i, minibatch %i/%i, test error of best '
                           'model %f %%') %
                          (epoch, minibatch_index + 1, n_train_batches,
                           test_score))
                    pred1 = numpy.array(model_prob(1)).tolist()
                    pred2 = numpy.array(result(1)).tolist()
                    with open("check.txt","a") as text_file:
                        text_file.write("{0}".format(pred1))
                        text_file.write("\n")
                        text_file.write("{0}".format(pred2))
                        text_file.write("\n")
                        text_file.close()
            if patience <= iter:
                done_looping = True
                break
    
    
    #scipy.io.savemat('./prediction_activity13.mat', mdict={'prediction':})
    end_time = time.clock()
    print('Optimization complete.')
    print('Best validation score of %f %% obtained at iteration %i,'\
          'with test performance %f %%' %
          (best_validation_loss, best_iter + 1, test_score))
    print >> sys.stderr, ('The code for file ' +
                          os.path.split(__file__)[1] +
                          ' ran for %.2fm' % ((end_time - start_time) / 60.))






#data_<name>.mat
if __name__ == '__main__':
    learning_rate=0.05
    n_epochs=100
    pathDataset = './'
    nameDataset='activity13'  #no .mat
    nkerns=[10, 50, 500]
    batch_size=1

    default = False;
    argv = sys.argv[1:]
    try:
        opts, args = getopt.getopt(argv,"n:p:",["nfile=","pfile="])
    except getopt.GetoptError:
        print ('use default parameter, otherwise -n <name Dataset> -p <path Dataset>')
        default = True;

    if not default:
        for opt, arg in opts:
            if opt in ("-n", "--nfile"):
                nameDataset = arg
            elif opt in ("-p", "--pfile"):
                pathDataset = arg




    print ("Train for: "+nameDataset)

    evaluate_lenet5(learning_rate, n_epochs, pathDataset, nameDataset,nkerns, batch_size)


