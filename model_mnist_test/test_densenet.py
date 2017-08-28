# Import the mnist data set:
import tensorflow as tf
from tensorflow.examples.tutorials.mnist import input_data
import sys

mnist = input_data.read_data_sets('MNIST_data', one_hot=True)

# mnist data is 28x28 images (784 pixels)

# Set up the network we want to test:

from models import densenet


# Set input data and label for training
data_tensor = tf.placeholder(tf.float32, [None, 784], name='x')
label_tensor = tf.placeholder(tf.float32, [None, 10], name='labels')

# Reshape the tensor to be 28x28:
x = tf.reshape(data_tensor, (tf.shape(data_tensor)[0], 28, 28, 1))


DenseNet = densenet.densenet()

EXTRA_NAME = "lr_5e-3_nblocks_2_nlpb_4_gr12_initkerel_3"
lr = 5e-3

logits = DenseNet.build_dense_net(input_tensor=x, n_output_classes=10,
                                  n_blocks=2, n_layers_per_block=5,
                                  include_fully_connected=False,
                                  growth_rate=12, is_training=True,
                                  n_initial_filters=32, initial_stride=1,
                                  initial_kernel=3,
                                  bottleneck=True, compression_factor=0.5,
                                  dropout_rate=0.5, weight_decay=1e-4,
                                  activation='softmax')


# Add a global step accounting for saving and restoring training:
with tf.name_scope("global_step") as scope:
    global_step = tf.Variable(
        0, dtype=tf.int32, trainable=False, name='global_step')

# Add cross entropy (loss)
with tf.name_scope("cross_entropy") as scope:
    cross_entropy = tf.reduce_mean(
        tf.nn.softmax_cross_entropy_with_logits(labels=label_tensor,
                                                logits=logits))
    loss_summary = tf.summary.scalar("Loss", cross_entropy)

# Add accuracy:
with tf.name_scope("accuracy") as scope:
    correct_prediction = tf.equal(
        tf.argmax(logits, 1), tf.argmax(label_tensor, 1))
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
    acc_summary = tf.summary.scalar("Accuracy", accuracy)

# Set up a training algorithm:
with tf.name_scope("training") as scope:
    train_step = tf.train.AdamOptimizer(lr).minimize(
        cross_entropy, global_step=global_step)


print "Setting up tensorboard writer ... "

LOGDIR = "logs"
ITERATIONS = 200
SAVE_ITERATION = 50

train_writer = tf.summary.FileWriter(LOGDIR + "/" + EXTRA_NAME + "/")
# snapshot_writer = tf.summary.FileWriter(LOGDIR + "/snapshot/")
saver = tf.train.Saver()

merged_summary = tf.summary.merge_all()
print type(merged_summary)

print "Initialize session ..."
with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())

    train_writer.add_graph(sess.graph)

    print "Begin training ..."
    # Run training loop
    for i in range(ITERATIONS):

        # Receive data (this will hang if IO thread is still running = this
        # will wait for thread to finish & receive data)
        data, label = mnist.train.next_batch(32)

        if i-1 % SAVE_ITERATION == 0:
            saver.save(
                sess,
                LOGDIR+"/checkpoints/densenet_pid_{}".format(EXTRA_NAME),
                global_step=global_step)

        # print training accuracy every 10 steps:
        # if i % 10 == 0:
        #     training_accuracy, loss_s, accuracy_s, = sess.run([accuracy, loss_summary, acc_summary],
        #                                                       feed_dict={data_tensor:data,
        #                                                                  label_tensor:label})
        #     train_writer.add_summary(loss_s,i)
        #     train_writer.add_summary(accuracy_s,i)

            # sys.stdout.write('Training in progress @ step %d accuracy %g\n' % (i,training_accuracy))
            # sys.stdout.flush()

        [l, a, summary, _] = sess.run([cross_entropy, accuracy, merged_summary, train_step], feed_dict={
            data_tensor: data, label_tensor: label})
        train_writer.add_summary(summary, i)
        sys.stdout.write(
            'Training in progress @ step %d, loss %g, accuracy %g\r' % (i, l, a))
        sys.stdout.flush()

    print "\nFinal training loss {}, accuracy {}".format(l, a)
    data, label = mnist.test.next_batch(500)
    
    [l, a, summary, _] = sess.run([cross_entropy, accuracy, merged_summary, train_step], feed_dict={
            data_tensor: data, label_tensor: label})
    print "\nTesting loss {}, accuracy {}".format(l, a)
