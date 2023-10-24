"""CLI tool to execute cpx_e tasks."""
from cpx_io.cpx_system.cpx_e import CPX_E

def add_cpx_e_parser(subparsers):
    """Adds arguments to a provided subparsers instance"""
    parser_position = subparsers.add_parser('cpx-e')
    parser_position.set_defaults(func=cpx_e_func)

    parser_position.add_argument('-r', '--read-register', help='Register to be read')


def cpx_e_func(args):
    """Executes subcommand based on provided arguments"""
    cpx_e = CPX_E(args.ip_address)
    register_value = cpx_e.readData(int(args.read_register))
    print(f"Value: {register_value}")