from tensorflow.keras import backend as KB

from spektral.layers import ops
from spektral.layers.convolutional.conv import Conv
from spektral.utils import normalized_laplacian, rescale_laplacian, chebyshev_reparam_weights


class ChebConv2(Conv):
    r"""
    A Chebyshev convolutional layer from the paper

    > [Convolutional Neural Networks on Graphs with Chebyshev Approximation, Revisited]
    (https://arxiv.org/pdf/2202.03580.pdf)<br>
    > He, Mingguo, Zhewei Wei, and Ji-Rong Wen

    **Input**

    - Node features of shape `([batch], n_nodes, n_node_features)`;
    - A list of K Chebyshev polynomials of shape
    `[([batch], n_nodes, n_nodes), ..., ([batch], n_nodes, n_nodes)]`; can be computed with
    `spektral.utils.convolution.chebyshev_filter`.

    **Output**

    - Node features with the same shape of the input, but with the last
    dimension changed to `channels`.

    **Arguments**

    - `channels`: number of output channels;
    - `K`: order of the Chebyshev polynomials;
    - `activation`: activation function;
    - `use_bias`: bool, add a bias vector to the output;
    - `kernel_initializer`: initializer for the weights;
    - `bias_initializer`: initializer for the bias vector;
    - `kernel_regularizer`: regularization applied to the weights;
    - `bias_regularizer`: regularization applied to the bias vector;
    - `activity_regularizer`: regularization applied to the output;
    - `kernel_constraint`: constraint applied to the weights;
    - `bias_constraint`: constraint applied to the bias vector.

    """

    def __init__(
        self,
        channels,
        K=1,
        activation=None,
        use_bias=True,
        kernel_initializer="glorot_uniform",
        bias_initializer="zeros",
        kernel_regularizer=None,
        bias_regularizer=None,
        activity_regularizer=None,
        kernel_constraint=None,
        bias_constraint=None,
        **kwargs
    ):
        super().__init__(
            activation=activation,
            use_bias=use_bias,
            kernel_initializer=kernel_initializer,
            bias_initializer=bias_initializer,
            kernel_regularizer=kernel_regularizer,
            bias_regularizer=bias_regularizer,
            activity_regularizer=activity_regularizer,
            kernel_constraint=kernel_constraint,
            bias_constraint=bias_constraint,
            **kwargs
        )
        self.channels = channels
        self.K = K

    def build(self, input_shape):
        assert len(input_shape) >= 2
        input_dim = input_shape[0][-1]
        self.kernel = self.add_weight(
            shape=(self.K, input_dim, self.channels),
            initializer=self.kernel_initializer,
            name="kernel",
            regularizer=self.kernel_regularizer,
            constraint=self.kernel_constraint,
        )
        #print(self.kernel)
        print(self.kernel.shape)
        # print(self.kernel[0].shape)
        #ret = chebyshev_reparam_weights(self.K, self.kernel, 0)
        if self.use_bias:
            self.bias = self.add_weight(
                shape=(self.channels,),
                initializer=self.bias_initializer,
                name="bias",
                regularizer=self.bias_regularizer,
                constraint=self.bias_constraint,
            )
        print("HALLO CHEBCONV 2")
        self.built = True

    def call(self, inputs, mask=None):
        x, a = inputs

        T_0 = x
        output = KB.dot(T_0, chebyshev_reparam_weights(self.K, self.kernel, 0))

        if self.K > 1:
            T_1 = ops.modal_dot(a, x)
            output += KB.dot(T_1, chebyshev_reparam_weights(self.K, self.kernel, 1))

        for k in range(2, self.K):
            T_2 = 2 * ops.modal_dot(a, T_1) - T_0
            output += KB.dot(T_2, chebyshev_reparam_weights(self.K, self.kernel, k))
            T_0, T_1 = T_1, T_2

        if self.use_bias:
            output = KB.bias_add(output, self.bias)
        if mask is not None:
            output *= mask[0]
        output = self.activation(output)

        return output

    @property
    def config(self):
        return {"channels": self.channels, "K": self.K}

    @staticmethod
    def preprocess(a):
        a = normalized_laplacian(a)
        a = rescale_laplacian(a)
        return a
