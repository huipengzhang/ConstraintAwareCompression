from __future__ import print_function
from __future__ import division
import sys
import os
import logging
import ConfigParser
os.environ['GLOG_minloglevel'] = '0'
import caffe
caffe.set_device(0)
caffe.set_mode_gpu()


def test_accuracy(iter_cnt, solver, test_iters, output_caffemodel):
    solver.test_nets[0].share_with(solver.net)
    accuracy = 0
    loss = 0
    for i in range(test_iters):
        solver.test_nets[0].forward()
        accuracy += solver.test_nets[0].blobs['accuracy'].data
        loss += solver.test_nets[0].blobs['loss'].data
    accuracy /= test_iters
    loss /= test_iters
    logging.info('Test in iteration {}, accuracy: {:.4f}, loss: {:.2f}'.format(iter_cnt, accuracy, loss))
    solver.net.save(output_caffemodel)
    logging.info('Model saved in {}'.format(output_caffemodel))
    return accuracy


def create_solver_file(solver_file, finetune_net, learning_rate, disp_interval, momentum):
    # create fine-tune solver
    with open(solver_file, 'w') as fo:
        fo.write('net: "{}"\n'.format(finetune_net))
        fo.write('test_iter: {}\n'.format(1))
        fo.write('test_interval: {}\n'.format(1000000))
        fo.write('base_lr: {}\n'.format(learning_rate))
        fo.write('lr_policy: "{}"\n'.format('step'))
        fo.write('stepsize: {}\n'.format(1000000))
        fo.write('display: {}\n'.format(disp_interval))
        fo.write('momentum: {}\n'.format(momentum))
        fo.write('solver_mode: {}\n'.format('GPU'))


def fine_tune(input_caffemodel, finetune_net, output_caffemodel, config_file, solver_file, log_file):
    """
    fine-tune until one of two requirements are satisfied: acc > min_acc or iter > max_iter
    :return:
    """
    # read configuration
    config = ConfigParser.RawConfigParser()
    config.read(config_file)
    min_acc = config.getfloat('fine-tuning', 'min_acc')
    max_iter = config.getint('fine-tuning', 'max_iter')
    base_lr = config.getfloat('fine-tuning', 'base_lr')
    momentum = config.getfloat('fine-tuning', 'momentum')
    test_iters = config.getint('fine-tuning', 'test_iters')
    test_interval = config.getint('fine-tuning', 'test_interval')
    disp_interval = config.getint('fine-tuning', 'disp_interval')
    step_iters = config.getint('fine-tuning', 'step_iters')

    # some fine-tuning parameters
    best_val_acc = 0
    best_val_iter = 0

    if os.path.exists(output_caffemodel):
        output_file = open(log_file, 'a+')
    else:
        output_file = open(log_file, 'w')
    sys.stdout = output_file
    sys.stderr = output_file
    logging.basicConfig(level=logging.INFO, format='%(asctime)s, %(levelname)s: %(message)s',
                        datefmt="%Y-%m-%d %H:%M:%S")

    learning_rate = base_lr
    logging.info('Current learning rate is {}'.format(learning_rate))
    create_solver_file(solver_file, finetune_net, learning_rate, disp_interval, momentum)
    solver = caffe.get_solver(solver_file)
    if not os.path.exists(output_caffemodel):
        solver.net.copy_from(input_caffemodel)
        logging.info('Fine-tune caffemodel from {}'.format(input_caffemodel))
    else:
        solver.net.copy_from(output_caffemodel)
        logging.info('Resume fine-tuning from {}'.format(output_caffemodel))

    iter_cnt = 0
    while iter_cnt < max_iter:
        # test
        if iter_cnt % test_interval == 0:
            # switch net to test mode
            acc = test_accuracy(iter_cnt, solver, test_iters, output_caffemodel)
            if acc > best_val_acc:
                best_val_acc = acc
                best_val_iter = iter_cnt
            if iter_cnt == 0:
                accuracy_before = acc
            # not final fine-tuning
            if acc >= min_acc:
                break

        # fine-tune
        solver.step(step_iters)
        loss = solver.net.blobs['loss'].data
        iter_cnt += step_iters
        if iter_cnt % disp_interval == 0 or iter_cnt == max_iter:
            logging.info('Training iteration {}, loss: {:.2f}'.format(iter_cnt, loss))

    # test final accuracy
    accuracy_after = test_accuracy(iter_cnt, solver, test_iters, output_caffemodel)
    logging.info('Accuracy before: {:.4f}'.format(accuracy_before))
    logging.info('Accuracy after: {:.4f}'.format(accuracy_after))
    logging.info('Best validation accuracy {:.4f} in iterations {}'.format(best_val_acc, best_val_iter))
    logging.info('Total iterations: {}'.format(iter_cnt))
    logging.info('Fine-tuning ends')
    output_file.close()


if __name__ == '__main__':
    assert len(sys.argv) == 7
    fine_tune(*sys.argv[1:])
