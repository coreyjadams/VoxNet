import numpy as np

def anchors_whctrs_to_minmax(anchors, in_place = False):
    """
    Map anchors from the (x_ctr, y_ctr, width, height) format
    to the (x_min, y_min, x_max, y_max) format

    This should work equally well for np arrays or tf tensors
    """

    if not in_place:
        anchors = np.copy(anchors)

    # Move the centers to be the minima:
    anchors[:,0] -= 0.5*anchors[:,2]
    anchors[:,1] -= 0.5*anchors[:,3]

    # Add the width to the start to get the max:
    anchors[:,2] += anchors[:,0] 
    anchors[:,3] += anchors[:,1] 

    return anchors

def anchors_minmax_to_whctrs(anchors, in_place = False):
    """
    Map anchors from the (x_min, y_min, x_max, y_max) format
    to the (x_ctr, y_ctr, width, height) format

    This should work equally well for np arrays or tf tensors
    """
    if not in_place:
        anchors = np.copy(anchors)
    # Calculate the widths:
    anchors[:,2] = anchors[:2] - anchors[:,0]
    anchors[:,3] = anchors[:3] - anchors[:,1]

    # Move the min to the center:
    anchors[:,0] += 0.5*anchors[:,2]
    anchors[:,1] += 0.5*anchors[:,3]

    return anchors

def pad_anchors(input_anchors, n_tiles_x=32, n_tiles_y=32, 
                step_size_x=16, step_size_y=16):
    """
    Take a set of anchors and expand them to cover the full image.
    Anchors need to be in the (x_ctr, y_ctr, width, height) format.

    There is no check on step_size, so you can always make it negative
    to pad the list of anchors in the opposite direction.
    """
    n_input_anchors = len(input_anchors)
    
    # Map the main anchors to cover every n pixels:
    _list_of_anchors = np.tile(input_anchors, reps=(n_tiles_x,n_tiles_y,1,1))
    
    for i in xrange(n_tiles_x):
        _list_of_anchors[i,:,:,0] += step_size_x*i
    for i in xrange(n_tiles_y):
        _list_of_anchors[:,i,:,1] += step_size_y*i

    # Flatten the result into a list of anchors (final shape [n_anchors, 4])
    return np.reshape(_list_of_anchors, (n_input_anchors*n_tiles_x*n_tiles_y, 4))


def generate_anchors(base_size = 16, ratios = [0.5, 1, 2.0], 
                      scales = 2**np.arange(4,7)):
    """
    Generate anchors.
    For each ratio and scale, there will be an anchor generated
    with area of (scale*base_size)**2, centered at 
    (base_size/2, base_size/2), with aspect ratio X:Y of ratio
    
    Anchors come out unordered.
    
    """
    n_anchors = len(ratios)*len(scales)

    base_anchor = np.array([int(base_size*0.5), 
                            int(base_size*0.5), 
                            base_size, 
                            base_size], np.float32) 
    # First, generate a list of anchors of the appropriate area:
    scaled_anchors = np.tile(base_anchor,(len(scales), 1))
    final_anchors = np.zeros((len(scales),len(ratios), 4), np.float32)
    for s, i in zip(scales, xrange(len(scales))):
        scaled_anchors[i,2:] *= s
        for r, j in zip(ratios, xrange(len(ratios))):
            t = np.copy(scaled_anchors[i])
            t[2] *= np.sqrt(r)
            t[3] *= 1./np.sqrt(r)
            final_anchors[i,j] = np.round(t)
    return np.reshape(final_anchors, (n_anchors, 4))


def numpy_IoU_xyctrs(bb1, bb2):
    """
    @brief      Compute the Intersection over Union for two bounding boxes
    
    @param      bb1   Bounding Box 1, as (x_center, y_center, width, height)
                    or (n1, x_center, y_center, width, height)
    @param      bb2   Bounding Box 2, as (x_center, y_center, width, height)
                    or (n2, x_center, y_center, width, height)
    
    @return     Intersection over Union value, between 0 and 1
    """

    # There should be at least one anchor, but maybe more.  
    # If the number of dimensions is only 1 (so it's just
    # one anchor), reshape the array to allow the slicing
    # to work properly:
    
    if bb1.ndim == 1:
        bb1 = np.reshape(bb1, (1,) + bb1.shape)
    if bb2.ndim == 1:
        bb2 = np.reshape(bb2, (1,) + bb2.shape)

    # Now, n1 and n2 can represent the number of anchors:
    n_1 = bb1.shape[0]
    n_2 = bb2.shape[0]

    # Want the IoU for every bb1 to every bb2, so tile them into
    # long 1D arrays to allow slicing:
    bb1_arr = np.reshape(np.tile(bb1, [1, n_2]), (n_1*n_2, 4))
    bb2_arr = np.tile(bb2, [n_1, 1])


    x1 = np.max((bb1_arr[:,0] - 0.5*bb1_arr[:,2], 
                bb2_arr[:,0] - 0.5*bb2_arr[:,2]),
                axis=0)
    y1 = np.max((bb1_arr[:,1] - 0.5*bb1_arr[:,3], 
                bb2_arr[:,1] - 0.5*bb2_arr[:,3]),
                axis=0)
    x2 = np.min((bb1_arr[:,0] + 0.5*bb1_arr[:,2], 
                bb2_arr[:,0] + 0.5*bb2_arr[:,2]),
                axis=0)
    y2 = np.min((bb1_arr[:,1] + 0.5*bb1_arr[:,3], 
                bb2_arr[:,1] + 0.5*bb2_arr[:,3]),
                axis=0)

    w = x2 - x1
    h = y2 - y1

    inter = w*h

    aarea  = (bb1_arr[:,3])* (bb1_arr[:,2])
    barea  = (bb2_arr[:,3])* (bb2_arr[:,2])

    denom = aarea + barea - inter
    mask = (denom == 0)
    denom[mask] = 0.1

    IoU = inter / (denom)
    IoU[mask] = 0
    IoU[w <= 0] = 0
    IoU[h <= 0] = 0
    
    return np.squeeze(np.reshape(IoU, (n_1,n_2)))


def numpy_IoU_minmax(bb1, bb2):
    """
    @brief      Compute the Intersection over Union for two bounding boxes
    
    @param      bb1   Bounding Box 1, as (x_min, y_min, x_max, y_max)
                    or (n1, x_min, y_min, x_max, y_max)
    @param      bb2   Bounding Box 2, as (x_min, y_min, x_max, y_max)
                    or (n1, x_min, y_min, x_max, y_max)
    
    @return     Intersection over Union value, between 0 and 1
    """

    # There should be at least one anchor, but maybe more.  
    # If the number of dimensions is only 1 (so it's just
    # one anchor), reshape the array to allow the slicing
    # to work properly:
    
    if bb1.ndim == 1:
        bb1 = np.reshape(bb1, (1,) + bb1.shape)
    if bb2.ndim == 1:
        bb2 = np.reshape(bb2, (1,) + bb2.shape)

    # Now, n1 and n2 can represent the number of anchors:
    n_1 = bb1.shape[0]
    n_2 = bb2.shape[0]


    # Want the IoU for every bb1 to every bb2, so tile them into
    # long 1D arrays to allow slicing:
    bb1_arr = np.reshape(np.tile(bb1, [1, n_2]), (n_1*n_2, 4))
    bb2_arr = np.tile(bb2, [n_1, 1])


    x1 = np.max((bb1_arr[:,0], 
                bb2_arr[:,0]),
                axis=0)
    y1 = np.max((bb1_arr[:,1], 
                bb2_arr[:,1]),
                axis=0)
    x2 = np.min((bb1_arr[:,2], 
                bb2_arr[:,2]),
                axis=0)
    y2 = np.min((bb1_arr[:,3], 
                bb2_arr[:,3]),
                axis=0)

    w = x2 - x1
    h = y2 - y1

    inter = w*h

    aarea  = (bb1_arr[:,3] - bb1_arr[:,1])*(bb1_arr[:,2] - bb1_arr[:,0])
    barea  = (bb2_arr[:,3] - bb2_arr[:,1])*(bb2_arr[:,2] - bb2_arr[:,0])

    denom = aarea + barea - inter
    mask = (denom == 0)
    denom[mask] = 0.1

    IoU = inter / (denom)
    IoU[mask] = 0
    IoU[w <= 0] = 0
    IoU[h <= 0] = 0
    
    return np.squeeze(np.reshape(IoU, (n_1,n_2)))


def compute_IoU(bb1_arr, bb2_arr):
    """
    @brief      Compute the Intersection over Union for two bounding boxes
    
    @param      bb1_arr   Bounding Box 1 list, as 
                (n_boxes, x_center, y_center, width, height)
    @param      bb2_arr   Bounding Box 2, as 
                (n_boxes, x_center, y_center, width, height)
    
    @return     Intersection over Union value, between 0 and 1, 
                array of shape (bb1_arr, bb2_arr)
    """
    
    # There are assumed to be a fixed number of bb for truths and anchors coming in, 
    # such that this is OK to be vectorized:
    
    n_1 = bb1_arr.get_shape().as_list()[0]
    n_2 = bb2_arr.get_shape().as_list()[0]

    bb1_arr = tf.reshape(tf.tile(bb1_arr, [1, n_2]), (n_1*n_2, 4))
    bb2_arr = tf.tile(bb2_arr, [n_1, 1])

    # print bb1_arr.get_shape()
    # print bb2_arr.get_shape()

    x1 = tf.maximum(bb1_arr[:,0]  - 0.5*bb1_arr[:,2], 
                    bb2_arr[:,0] - 0.5*bb2_arr[:,2])
    y1 = tf.maximum(bb1_arr[:,1]  - 0.5*bb1_arr[:,3], 
                    bb2_arr[:,1] - 0.5*bb2_arr[:,3])
    x2 = tf.minimum(bb1_arr[:,0] + 0.5*bb1_arr[:,2], 
                    bb2_arr[:,0] + 0.5*bb2_arr[:,2])
    y2 = tf.minimum(bb1_arr[:,1] + 0.5*bb1_arr[:,3], 
                    bb2_arr[:,1] + 0.5*bb2_arr[:,3])

    w = x2 - x1 +1
    h = y2 - y1 +1

    # Instead of trying to find all the negative values and such ...
    # Just use ReLU to map w and h to positive values:
    w = tf.nn.relu(w)
    h = tf.nn.relu(h)


    inter = w*h 
    aarea  = (bb1_arr[:,3]  + 1) * (bb1_arr[:,2]  + 1)
    barea  = (bb2_arr[:,3] + 1) * (bb2_arr[:,2] + 1)

    IoU = tf.divide(inter , (aarea + barea - inter))

    return tf.reshape(IoU, (n_1, n_2))
