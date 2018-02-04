from __future__ import print_function
from __future__ import division
import sys
import os
import logging
os.environ['GLOG_minloglevel'] = '2'
sys.path.append('/local-scratch/changan-home/SkimCaffe/python')
import caffe

caffe.set_device(0)
caffe.set_mode_gpu()


def fine_tune(input_caffemodel, solver_file, output_caffemodel, min_acc, max_iter, log_file=None):
    """
    fine-tune until one of two requirements are satisfied: acc > min_acc or iter > max_iter
    :param input_caffemodel:
    :param solver_file:
    :param output_caffemodel:
    :param min_acc:
    :param max_iter:
    :return:
    """
    # some fine-tuning parameters
    test_iters = 50
    test_interval = 1000
    disp_interval = 10
    if log_file is not None:
        logging.basicConfig(filename=log_file, filemode='w', level=logging.INFO)
    else:
        logging.basicConfig(filename='results/finetuning.log', filemode='w', level=logging.INFO)
    min_acc = float(min_acc)
    max_iter = int(max_iter)

    solver = caffe.get_solver(solver_file)
    solver.net.copy_from(input_caffemodel)
    iter = 0
    while iter < max_iter:
        # test
        if iter != 0 and iter % test_interval == 0:
            # switch net to test mode
            solver.test_nets[0].share_with(solver.net)
            accuracy = 0
            for i in range(test_interval):
                accuracy += solver.test_nets[0].forward()['acc']
            accuracy /= test_iters
            logging.info('Test accuracy: {:.2f}'.format(accuracy))
            if accuracy > min_acc:
                break

        # fine-tune
        solver.step(1)
        loss = solver.net.blobs['loss'].data.copy()
        if iter % disp_interval == 0 or iter + 1 == max_iter:
            logging.info('Training iteration {}, loss: {:.2f}'.format(iter, loss))
        iter += 1

    # save learned weights
    solver.net.save(output_caffemodel)


if __name__ == '__main__':
    assert len(sys.argv) == 7
    fine_tune(*sys.argv[1:])