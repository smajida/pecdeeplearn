import pecdeeplearn as pdl
import data_path

if __name__ == '__main__':

    experiment_name = 'single_conv_single_landmark'
    exp = pdl.utils.Experiment(data_path.get(), experiment_name)

    test = exp.unpickle_volume('test_volume')
    test.show_slice(0)

    pred =exp.unpickle_volume('predicted_volume')
    pred.show_slice(0)