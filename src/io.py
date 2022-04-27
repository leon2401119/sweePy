import logging
import re
import copy
import random

logging.getLogger(__name__)


def prefill_cmd(configs,GAname,**kwargs):
    GA_spec = configs['GAspecs'][GAname]

    argv = GA_spec["io"]["argv"]
    tokens = re.findall('\w+|\[\w+\]|-+\w+=|.',argv)

    for idx, token in enumerate(tokens):
        if token in ['pop','seed']:      # reserved
            continue

        if re.match('\w+',token):        # required arg
            required = True
        elif re.match('\[\w+\]',token):  # optional arg
            token = token[1:-1]          # strip the [ and ]
            required = False
        else:                            # any other things, generally including seperators like spaces or tabs
            continue

        ## Sequentially search for value replacement, priority from H to L is kwargs -> mappings -> basics -> fixed fields

        # 1. prefill kwarg
        try:
            target = kwargs[token]
            tokens[idx] = str(target)
            logging.info(f'{GAname} argv substitution : "{token}" -> {target}  (kwargs)')
            continue
        except Exception as e:
            logging.debug(f'No match for "{token}" in kwargs')

        # 2. prefill mapping
        mapped = False
        for mapping in GA_spec['io']['mappings']:
            src = mapping['to']
            if src == token:
                try:
                    target = configs['basics'][mapping['from']]
                    tokens[idx] = str(mapping['map'][target])
                    logging.info(f'{GAname} argv substitution : "{token}" -> "{target}" -> {tokens[idx]}  (mappings)')
                    mapped = True
                    break
                except Exception as e:
                    logging.error(f'Found "{src}" to replace with "{target}", but the value of "{target}" is not specified in the basics secion')
                    exit()

        if mapped:
            continue
        else:
            logging.debug(f'No match for "{token}" in mappings')

        # 3. prefill basics
        try:
            target = configs['basics'][token]
            assert type(target) in [int,float,str]
            if type(target) in [int,float]:  # number
                tokens[idx] = str(target)
            else:                             # python statement
                tokens[idx] = str(eval(target))
            logging.info(f'{GAname} argv substitution : "{token}" -> {target}  (basics)')
            continue
        except Exception as e:
            logging.debug(f'No match for "{token}" in basics')

        # 4. prefill fixed fileds
        try:
            target = GA_spec['io']['fixed_fields'][token]
            assert type(target) in [int,float,str]
            if type(target) in [int,float]:  # number
                tokens[idx] = str(target)
            else:                             # python statement
                tokens[idx] = str(eval(target))
            logging.info(f'{GAname} argv substitution : "{token}" -> {target}  (fixed fields)')
            continue
        except Exception as e:
            logging.debug(f'No match for "{token}" in fixed fields')

        
        if required:  # token is a required arg and no match was found
            #logging.error(f'No match for "{token}", which is required in the argv of {GAname}')
            #exit()
            continue

        else:         # token is an optional keyword and is not specified anywhere
            logging.warning(f'No match for "{token}", since it is optional it will be discarded from argv')
            tokens[idx] = ''   # clear it here
   

    return f'./{GA_spec["bin"]} {"".join(tokens)}'


def prefill_env(configs,GAname,**kwargs):
    GA_spec = configs['GAspecs'][GAname]

    try:
        raw_env = copy.deepcopy(GA_spec['io']['envs']) # pitfall: shallow copy modifies the contents of configs
    except:
        raw_env = {}

    for key, val in raw_env.items():
        # prefill kwargs
        if val in kwargs.keys():
            raw_env[key] = str(kwargs[val])

    return raw_env


def finalize_cmd(cmd, pop):
    # finalize reserved tokens

    if 'pop ' in cmd:
        cmd.replace('pop ',f'{pop} ')
    elif cmd[-3:] == 'pop':
        cmd = cmd[:-3] + str(pop)
    else:
        logging.error(f'Cannot substitute pop for "{cmd}"')
        exit()

    if 'seed ' in cmd:
        cmd.replace('seed ', str(random.randint(0,1000)))
    elif cmd[-4:] == 'seed':
        cmd = cmd[:-4] + str(random.randint(0,1000))

    return cmd.replace('pop ',f'{pop} ')


def parse_output(configs, GAname, out_str):
    #print(out_str) ## DEBUG
    stdout_regex = configs['GAspecs'][GAname]['io']['stdout']
    tokens = re.findall('\w+|\[\w+\]|.', stdout_regex)

    out_dict = {}

    for req_tok in ['nfe',]:
        if req_tok not in tokens:
            logging.error(f'{req_tok} is non-optional for sweeping, and should be specified in stdout of {GAname}')
            exit()

    for token in tokens:
        if re.match('\w+',token):        # a name is given, which should correspond to a number
            r = re.search('[-+]?([0-9]*[.])?[0-9]+([eE][-+]?\d+)?', out_str)    # floating point / scientific notation
            if r:
                value = float(out_str[r.start():r.end()])
                out_dict[token] = value
                logging.debug(f'{GAname} stdout parsing : {token} = {str(value)}')
                out_str = out_str[r.end():]
                continue

            r = re.search('[-+]?[0-9]+', out_str)                               # interger
            if r:
                value = int(out_str[r.start():r.end()])
                logging.debug(f'{GAname} stdout parsing : {token} = {str(value)}')
                out_dict[token] = value
                out_str = out_str[r.end():]
                continue
            else:
                logging.debug(f'{GAname} stdout parsing : "{token}" not matched with any value')
                return None

        else:                            # seperator (e.g. spaces, newlines, ...etc)
            idx = out_str.find(token)
            
            if idx == -1:
                logging.debug(f'{GAname} stdout parsing : seperator "{token}" not matched')
                return None

            logging.debug(f'{GAname} stdout parsing : "{token}" consumed')
            out_str = out_str[idx+1:]

    return out_dict
