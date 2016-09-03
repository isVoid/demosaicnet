"""Models for 'Deep Joint demosaicking and Denoising'."""

from caffe import layers as L, params as P
import caffe

__all__ = ['demosaic']


def _convolution(bottom, width, ksize, pad=True):
    """Parametrized convolution layer."""
    if pad:
        padding = (ksize-1)/2
    else:
        padding = 0

    return L.Convolution(
        bottom=bottom,
        param=[{'lr_mult': 1, 'decay_mult': 1},
               {'lr_mult': 2, 'decay_mult': 0}],
        convolution_param={
            'num_output': width,
            'kernel_size': ksize,
            'pad': padding,
            'weight_filler': {
                'type': 'msra',
                'variance_norm': P.Filler.AVERAGE,
            },
            'bias_filler': {
                'type': 'constant',
                'value': 0,
            }
        })

#pylint: disable=too-many-arguments
def demosaic(depth, width, ksize, batch_size,
             mosaic_type='bayer', trainset=None,
             min_noise=0, max_noise=0, pad=True):
    """Network to denoise/demosaic Bayer arrays."""

    if mosaic_type not in ['bayer', 'xtrans']:
        raise Exception('Unknown mosaic type "{}".'.format(mosaic_type))

    net = caffe.NetSpec()

    is_train_mode = (trainset is not None)
    add_noise = (min_noise > 0 or max_noise > 0)

    if add_noise and min_noise > max_noise:
        raise ValueError('min noise is greater than max_noise')

    if is_train_mode:  # Build the train network
        # Read from an LMDB database for train and validation sets
        net.demosaicked = L.Data(
            data_param={'source': trainset,
                        'backend': P.Data.LMDB,
                        'batch_size': batch_size},
            transform_param={'scale': 0.00390625})

        # Extend the data
        net.offset = L.Python(bottom='demosaicked',
                              python_param={'module':'demosaicnet.layers',
                                            'layer': 'RandomOffsetLayer',
                                            'param_str': '{"offset_x": 1, "offset_y":1}'})
        net.flip = L.Python(bottom='offset',
                            python_param={'module':'demosaicnet.layers',
                                          'layer': 'RandomFlipLayer'})
        net.groundtruth = L.Python(bottom='flip',
                              python_param={'module':'demosaicnet.layers',
                                            'layer': 'RandomRotLayer'})

        # Add noise
        if add_noise:
            net.noisy, net.noise_level = L.Python(
                    ntop=2,
                    bottom='groundtruth',
                    python_param={'module':'demosaicnet.layers',
                                  'layer': 'AddGaussianNoiseLayer',
                                  'param_str': '{"min_noise": %f, "max_noise":%f}' % (min_noise, max_noise)})
            layer_to_mosaick = 'noisy'
        else:
            layer_to_mosaick = 'groundtruth'

        # ---------------------------------------------------------------------
        if mosaic_type == 'bayer':
            net.mosaick = L.Python(bottom=layer_to_mosaick,
                                   python_param={'module':'demosaicnet.layers',
                                                 'layer': 'BayerMosaickLayer'})
        else:
            net.mosaick = L.Python(bottom=layer_to_mosaick,
                                   python_param={'module':'demosaicnet.layers',
                                                 'layer': 'XTransMosaickLayer'})
        # ---------------------------------------------------------------------


    else:  # Build the test network
        net.mosaick = L.Input(shape=dict(dim=[batch_size, 3, 128, 128]))
        if add_noise:
            net.noise_level = L.Input(shape=dict(dim=[batch_size]))

    # -------------------------------------------------------------------------
    if mosaic_type == 'bayer':
        # Pack mosaick (2x2 downsampling)
        net.pack = L.Python(bottom='mosaick',
                            python_param={'module':'demosaicnet.layers',
                                          'layer': 'PackBayerMosaickLayer'})
        pre_noise_layer = 'pack'
    else:
        pre_noise_layer = 'mosaick'
    # -------------------------------------------------------------------------

    # Add noise input
    if add_noise:
        net.replicated_noise_level = L.Python(
                bottom=['noise_level', pre_noise_layer],
                python_param={'module':'demosaicnet.layers',
                              'layer': 'ReplicateLikeLayer'})
        net.pack_and_noise = L.Concat(bottom=[pre_noise_layer, 'replicated_noise_level'])

    # Process
    for layer_id in range(depth):
        name = 'conv{}'.format(layer_id+1)
        if layer_id == 0:
            if add_noise:
                bottom = 'pack_and_noise'
            else:
                bottom = pre_noise_layer
        else:
            bottom = 'conv{}'.format(layer_id)

        if layer_id == depth-1:
            nfilters = 12
        else:
            nfilters = width

        net[name] = _convolution(bottom, nfilters, ksize, pad=pad)
        net['relu{}'.format(layer_id+1)] = L.ReLU(net[name], in_place=True)

    # -------------------------------------------------------------------------
    if mosaic_type == 'bayer':
        # Unpack result
        net.unpack = L.Python(bottom='conv{}'.format(depth),
                              python_param={'module':'demosaicnet.layers',
                                            'layer': 'UnpackBayerMosaickLayer'})
        unpack_layer = 'unpack'
    else:
        unpack_layer = 'conv{}'.format(depth)
    # -------------------------------------------------------------------------

    # Fast-forward input mosaick
    if not pad:
        net.cropped_mosaick = L.Python(bottom=['mosaick', unpack_layer],
                                       python_param={'module':'demosaicnet.layers',
                                                     'layer': 'CropLikeLayer'})
        mosaick_layer = 'cropped_mosaick'
    else:
        mosaick_layer = 'mosaick'
    net.residual_and_mosaick = L.Concat(bottom=[unpack_layer, mosaick_layer])

    # Full-res convolution
    net['fullres_conv'] = _convolution('residual_and_mosaick', width, ksize, pad=pad)
    net['fullres_relu'] = L.ReLU(net['fullres_conv'], in_place=True)
    net['output'] = _convolution('fullres_conv', 3, 1)

    if trainset is not None:  # Add a loss for the train network
        # Output
        if not pad:
            net.cropped_groundtruth = L.Python(bottom=['groundtruth', 'output'],
                                          python_param={'module':'demosaicnet.layers',
                                                         'layer': 'CropLikeLayer'})
            gt_layer = 'cropped_groundtruth'
        else:
            gt_layer = 'groundtruth'

        # TODO: normalized Euclidean loss
        net['loss'] = L.EuclideanLoss(bottom=['output', gt_layer],
                                      loss_weight=1.0/(128*128*3))

    return net
#pylint: enable=too-many-arguments