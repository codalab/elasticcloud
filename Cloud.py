import click
from ElasticCloudAdapter import ElasticCloudAdapter
from GCEAdapter import GCEAdapter

def adapter_choice(driver):
    if driver == 'gce':
        return GCEAdapter()
    else:
        raise NotImplementedError
    

@click.group()
def cli():
    pass

@cli.command()
@click.argument('driver', type=click.Choice(['gce']))
def control_load(driver):
    adapter = adapter_choice(driver)
    
    next_action, action_count = adapter.get_next_action()
    
    if next_action == ElasticCloudAdapter.ACTION_DO_NOTHING:
        click.echo('Service is in equilibrium. No need to shrink or expand right now!')

    for i in range(action_count):
        if next_action == ElasticCloudAdapter.ACTION_SHRINK:
            click.echo('Shrinking...')
            click.echo(adapter.shrink())
            
        if next_action == ElasticCloudAdapter.ACTION_EXPAND:
            click.echo('Expanding...')
            click.echo(adapter.expand())


@cli.command()
@click.argument('driver', type=click.Choice(['gce']))
def dump_state(driver):
    adapter = adapter_choice(driver)

    states = adapter.dump_state()
    click.echo('\n\nNode states:\n')
    output_format = '{0: <30} {1}'
    click.echo(output_format.format('Name', 'State'))
    for state in states:
        click.echo(output_format.format(state[0], state[1]))

@cli.command()
@click.argument('driver', type=click.Choice(['gce']))
def shrink(driver):
    adapter = adapter_choice(driver)
    click.echo('Shrinking...')
    click.echo(adapter.shrink())

@cli.command()
@click.argument('driver', type=click.Choice(['gce']))
def expand(driver):
    adapter = adapter_choice(driver)
    click.echo('Expanding...')
    click.echo(adapter.expand())
    
if __name__ == '__main__':
    cli()
