import argparse
import logging
import tarfile
import zipfile

import cv2
import torch


def clip_gradient(optimizer, grad_clip):
    """
    Clips gradients computed during backpropagation to avoid explosion of gradients.
    :param optimizer: optimizer with the gradients to be clipped
    :param grad_clip: clip value
    """
    for group in optimizer.param_groups:
        for param in group['params']:
            if param.grad is not None:
                param.grad.data.clamp_(-grad_clip, grad_clip)


def save_checkpoint(epoch, epochs_since_improvement, model, metric_fc, optimizer, acc, is_best):
    state = {'epoch': epoch,
             'epochs_since_improvement': epochs_since_improvement,
             'acc': acc,
             'model': model,
             'metric_fc': metric_fc,
             'optimizer': optimizer}
    # filename = 'checkpoint_' + str(epoch) + '_' + str(loss) + '.tar'
    filename = 'checkpoint.tar'
    torch.save(state, filename)
    # If this checkpoint is the best so far, store a copy so it doesn't get overwritten by a worse checkpoint
    if is_best:
        torch.save(state, 'BEST_checkpoint.tar')


class AverageMeter(object):
    """
    Keeps track of most recent, average, sum, and count of a metric.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


def adjust_learning_rate(optimizer, shrink_factor):
    """
    Shrinks learning rate by a specified factor.
    :param optimizer: optimizer whose learning rate must be shrunk.
    :param shrink_factor: factor in interval (0, 1) to multiply learning rate with.
    """

    print("\nDECAYING learning rate.")
    for param_group in optimizer.param_groups:
        param_group['lr'] = param_group['lr'] * shrink_factor
    print("The new learning rate is %f\n" % (optimizer.param_groups[0]['lr'],))


def accuracy(scores, targets, k=1):
    batch_size = targets.size(0)
    _, ind = scores.topk(k, 1, True, True)
    correct = ind.eq(targets.view(-1, 1).expand_as(ind))
    correct_total = correct.view(-1).float().sum()  # 0D tensor
    return correct_total.item() * (100.0 / batch_size)


def parse_args():
    parser = argparse.ArgumentParser(description='Train face network')
    # general
    parser.add_argument('--pretrained', type=bool, default=False, help='pretrained model')
    parser.add_argument('--end-epoch', type=int, default=1000, help='training epoch size.')
    parser.add_argument('--lr', type=float, default=0.001, help='start learning rate')
    parser.add_argument('--lr-step', type=int, default=10, help='period of learning rate decay')
    parser.add_argument('--optimizer', default='sgd', help='optimizer')
    parser.add_argument('--weight-decay', type=float, default=1e-4, help='weight decay')
    parser.add_argument('--mom', type=float, default=0.9, help='momentum')
    parser.add_argument('--batch-size', type=int, default=128, help='batch size in each context')
    parser.add_argument('--margin-m', type=float, default=0.5, help='angular margin m')
    parser.add_argument('--margin-s', type=float, default=64.0, help='feature scale s')
    parser.add_argument('--easy-margin', type=bool, default=False, help='easy margin')
    parser.add_argument('--focal-loss', type=bool, default=False, help='focal loss')
    parser.add_argument('--gamma', type=float, default=2.0, help='focusing parameter gamma')
    parser.add_argument('--checkpoint', type=str, default=None, help='checkpoint')
    args = parser.parse_args()
    return args


def get_logger():
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s \t%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger


def ensure_folder(folder):
    import os
    if not os.path.isdir(folder):
        os.mkdir(folder)


def draw_str(dst, target, s):
    x, y = target
    cv2.putText(dst, s, (x + 1, y + 1), cv2.FONT_HERSHEY_PLAIN, 1.0, (0, 0, 0), thickness=2, lineType=cv2.LINE_AA)
    cv2.putText(dst, s, (x, y), cv2.FONT_HERSHEY_PLAIN, 1.0, (255, 255, 255), lineType=cv2.LINE_AA)


def extract_zip(filename):
    print('Extracting {}...'.format(filename))
    zip_ref = zipfile.ZipFile(filename, 'r')
    zip_ref.extractall('data')
    zip_ref.close()


def extract_tgz(filename):
    print('Extracting {}...'.format(filename))
    with tarfile.open(filename) as tar:
        def is_within_directory(directory, target):
            
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
        
            prefix = os.path.commonprefix([abs_directory, abs_target])
            
            return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")
        
            tar.extractall(path, members, numeric_owner=numeric_owner) 
            
        
        safe_extract(tar, "data/test")
