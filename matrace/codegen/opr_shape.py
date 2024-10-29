import torch


def unary_shape(opr: str, input_shape: tuple) -> tuple:
  if opr in ('ctranspose', "'", 'transpose', ".'"):
    return input_shape[:-2] + (input_shape[-1], input_shape[-2])
  elif opr in ('uplus', '+', 'uminus', '-', '~', '!', 'not'):
    return input_shape
  else:
    raise ValueError(f"Unsupported unary operator: {opr}")


_broadcast_set = {
    '+', 'plus', '-', 'minus', '.*', 'times',
    './', 'rdivide', '.\\', 'ldivide',
    '.^', 'power',
    '<', 'lt', '>', 'gt', '<=', 'le', '>=', 'ge',  # cmp
    '~=', 'ne', '==', 'eq',  # cmp
    '&', '&&', 'and', '|', '||', 'or',  # logical
}


def binary_shape(opr: str, shape1: tuple, shape2: tuple) -> tuple:
  if opr in ('*', 'mtimes'):
    # matmul
    if len(shape1) < 2 or len(shape2) < 2:
      raise ValueError(
          "Both inputs must have at least 2 dimensions for matrix multiplication")
    return shape1[:-2] + (shape1[-2], shape2[-1])

  elif opr in ('/', 'mrdivide', '\\', 'mldivide'):
    # matdiv
    if len(shape1) < 2 or len(shape2) < 2:
      raise ValueError(
          "Both inputs must have at least 2 dimensions for matrix division")
    return shape1[:-2] + (
        (shape1[-2], shape2[-2]) if opr in ('/', 'mrdivide')
        else (shape2[-2], shape1[-2])
    )

  elif opr in ('^', 'mpower'):
    # matpow
    if len(shape1) < 2 or shape1[-2] != shape1[-1]:
      raise ValueError("First input must be a square matrix for matrix power")
    return shape1

  elif opr in _broadcast_set:
    return torch.broadcast_shapes(shape1, shape2)

  else:
    raise ValueError(f"Unsupported binary operator: {opr}")
