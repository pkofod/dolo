
class CompilerMatlab(object):

    def __init__(self, model, model_type=None, recipes=None):

        if model_type is None:
            model_type = model.__data__['model_type']


        self.model = model

        from dolo.symbolic.validator import validate
        if isinstance(model_type, str):
            from dolo.symbolic.recipes import recipes as recipes_dict
            if recipes is not None:
                recipes_dict.update(recipes)
            self.recipe = recipes_dict[model_type]
            validate(model, self.recipe)
        else:
            # if model_type is not a string, we assume it is a recipe (why ?)
            self.recipe = model_type


    def process_output(self, recipe=None, diff=False):

        recipe = self.recipe

        model = self.model
        parms = model.symbols_s['parameters']


        fun_text = ''

        for eqg in self.model.equations_groups:

            args = []

            is_a_definition = 'definition' in recipe['equation_type'][eqg]

            if is_a_definition:
                arg_specs = recipe['equation_type'][eqg]['rhs']
            else:
                arg_specs = recipe['equation_type'][eqg]


            arg_names = []
            for syms in arg_specs:
                [sgn,time] = syms
                args.append( [ s(time) for s in model.symbols_s[sgn] if sgn not in ('parameters',) ] )
                if time == 1:
                    stime = '_f'
                elif time == -1:
                    stime = '_p'
                else:
                    stime = ''
                arg_names.append( sgn + stime)

            equations = self.model.equations_groups[eqg]

            if is_a_definition:
                from dolo.compiler.common import solve_recursive_block
                equations = solve_recursive_block(equations)
                equations = [eq.rhs for eq in equations]
            else:
                equations = [eq.gap for eq in equations]

            from dolo.compiler.function_compiler_matlab import compile_multiargument_function
            txt = compile_multiargument_function(equations, args, arg_names, parms, fname = eqg, diff=diff)

            fun_text += txt


        # the following part only makes sense for fga models

        calib = model.calibration
        cc = calib.copy()
        cc.pop('parameters')
        cc.pop('shocks')
        cc.pop('covariances')
        steady_state = cc
        parameters_values = calib['parameters']

        if 'covariances' in calib:
            sigma_calib = 'calibration.sigma = {};\n'.format( str(calib['covariances']).replace('\n',';') )
        else:
            sigma_calib = {}



        funs_text = "functions = struct;\n"
        for fun_name in recipe['equation_type']:
            funs_text += 'functions.{0} = @{0};\n'.format(fun_name)

        ss_text = "calibration = struct;\n"
        for k,v in steady_state.iteritems():
            ss_text += 'calibration.{0} = {1};\n'.format( k, str(v).replace('\n',' ')  )
        ss_text += 'calibration.parameters = {0};\n'.format(str(parameters_values).replace('\n',' '))
        ss_text += sigma_calib


        var_text = "symbols = struct;\n"
        for vn, vg in model.symbols_s.iteritems():
            var_text += 'symbols.{0} = {{{1}}};\n'.format(vn, str.join(',', ["'{}'".format(e ) for e in vg]))

        full_text = '''

function [model] = get_model()


{var_text}

{calib_text}


{funs_text}

model = struct;
model.symbols = symbols;
model.functions = functions;
model.calibration = calibration;

end





{function_definitions}

'''.format(
            function_definitions = fun_text,
            funs_text = funs_text,
            calib_text = ss_text,
            var_text = var_text,
        )

        return full_text

if __name__ == '__main__':

    from dolo import *

    model = yaml_import('examples/global_models/rbc.yaml', compiler=None)
    comp = CompilerMatlab(model)

    print  comp.process_output(diff=True)

    print("******10")
    print("******10")
    print("******10")

    model = yaml_import('examples/global_models/optimal_growth.yaml', compiler=None)
    comp = CompilerMatlab(model)

    print  comp.process_output()





