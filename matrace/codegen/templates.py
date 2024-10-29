import ast
from matrace.codegen.ast_template import CodeTemplate


tpl_ref_obj = CodeTemplate('a.b', no_expr=True)
tpl_ref_arr = CodeTemplate('a[b]', no_expr=True)
tpl_asgn_name = CodeTemplate('b = c', mode='exec')
tpl_asgn_obj = CodeTemplate('a.b = c', mode='exec')
tpl_asgn_arr = CodeTemplate('a[b] = c', mode='exec')
tpl_call = CodeTemplate('a(b)', no_expr=True)

tpl_create_tensor = CodeTemplate(
    'torch.tensor(elem, dtype=dtype)', dtype=ast.Name('float'),
    no_expr=True,
)
tpl_create_tensor_no_dtype = CodeTemplate(
    'torch.tensor(elem)',
    no_expr=True,
)
tpl_cat_tensor = CodeTemplate(
    'torch.cat(tensors, dim=dim)', no_expr=True,
)
tpl_slice_tensor_row = CodeTemplate(
    't[..., i, :]', no_expr=True,
)