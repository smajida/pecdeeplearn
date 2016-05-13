from __future__ import division

import lasagne
import numpy as np
import nolearn.lasagne
import pecdeeplearn as pdl
import data_path
import time


# Create an experiment object to keep track of parameters and facilitate data
# loading and save_allowed.
exp = pdl.utils.Experiment(data_path.get(), 'single_conv_single_landmark')
exp.add_param('volume_depth', 20)
exp.add_param('min_seg_points', 100)
exp.add_param('patch_shape', [1, 41, 41])
exp.add_param('landmark', 'Sternal angle')
exp.add_param('filter_size', (21, 21))
exp.add_param('num_filters', 64)
exp.add_param('patch_num_dense_units', 1000)
exp.add_param('landmark_num_dense_units', 1000)
exp.add_param('batch_size', 5000)
exp.add_param('update_learning_rate', 0.0001)
exp.add_param('update_momentum', 0.9)
exp.add_param('max_epochs', 100)

# List and load all vols, then switch them to the axial orientation.
vol_list = exp.list_volumes()
vols = [exp.load_volume(vol) for vol in vol_list]
for vol in vols:
    vol.switch_orientation('acs')
pdl.utils.standardise_volumes(vols)

# Take a set of slices centred about the left nipple.
centre_slices = [int(vol.landmarks['Left nipple'][0]) for vol in vols]
vols = [vol[(centre_slices[i] - exp.params['volume_depth'] // 2):
            (centre_slices[i] + exp.params['volume_depth'] // 2)]
        for i, vol in enumerate(vols)]

# Strip away vols with little segmentation data.
vols = [vol for vol in vols
        if np.sum(vol.seg_data) > exp.params['min_seg_points']]

# Create training maps.
point_maps = [pdl.extraction.half_half_map(vol) for vol in vols]

# Create an Extractor.
ext = pdl.extraction.Extractor()

# Add features.
ext.add_feature(
    feature_name='patch',
    feature_function=lambda volume, point:
    pdl.extraction.patch(volume, point, exp.params['patch_shape'])
)
ext.add_feature(
    feature_name='landmark',
    feature_function=lambda volume, point:
    pdl.extraction.landmark_displacement(volume, point, exp.params['landmark'])
)

# Create the net.
net = nolearn.lasagne.NeuralNet(
    layers=[

        # Layers for the local patch.
        (lasagne.layers.InputLayer,
         {'name': 'patch',
          'shape': tuple([None] + exp.params['patch_shape'])}),
        (lasagne.layers.Conv2DLayer,
         {'name': 'conv', 'num_filters': exp.params['num_filters'],
          'filter_size': exp.params['filter_size']}),
        (lasagne.layers.DenseLayer,
         {'name': 'patch_dense',
          'num_units': exp.params['patch_num_dense_units']}),

        # Layers for the landmark displacement.
        (lasagne.layers.InputLayer,
         {'name': 'landmark', 'shape': (None, 3)}),
        (lasagne.layers.DenseLayer,
         {'name': 'landmark_dense',
          'num_units': exp.params['landmark_num_dense_units']}),

        # Layers for concatenation and output.
        (lasagne.layers.ConcatLayer,
         {'incomings': ['patch_dense', 'landmark_dense']}),
        (lasagne.layers.DenseLayer,
         {'name': 'output', 'num_units': 2,
          'nonlinearity': lasagne.nonlinearities.softmax}),

    ],

    # Optimization method.
    update=lasagne.updates.nesterov_momentum,
    update_learning_rate=exp.params['update_learning_rate'],
    update_momentum=exp.params['update_momentum'],

    # Other options.
    max_epochs=exp.params['max_epochs'],
    verbose=1
)

# Record information to be used for printing progress.
total_points = np.sum(point_maps)
start_time = time.time()

# Iterate through and train.
for i, (input_batch, output_batch) in \
        enumerate(ext.iterate_multiple(vols[:-1],
                                       point_maps[:-1],
                                       exp.params['batch_size'])):
    net.fit(input_batch, output_batch)
    pdl.utils.print_progress(start_time,
                             (i + 1) * exp.params['batch_size'],
                             total_points)
print("Training complete.")

# Save the network.
exp.save_network(net, 'net')

# Predict on the last volume.
test_volume = vols[-1]
predicted_volume = ext.predict(net, test_volume, exp.params['batch_size'])

# Save the volumes for comparison.
exp.pickle_volume(test_volume, 'test_volume')
exp.pickle_volume(predicted_volume, 'predicted_volume')

# Record the parameters
exp.record_params()