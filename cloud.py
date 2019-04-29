#!/usr/bin/env python3
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
def auto_scale(driver):
    adapter = adapter_choice(driver)

    adapter.update_all_states()
    states = adapter.dump_state()
    output_format = '{0: <30} {1}'
    click.echo(output_format.format('Name', 'State'))
    for name in states:
        click.echo(output_format.format(name, states[name]['status']))
    
    next_action, action_count = adapter.get_next_action()
    
    if next_action == ElasticCloudAdapter.ACTION_DO_NOTHING:
        click.echo('Service is in equilibrium. No need to shrink or expand right now!')

    if next_action == ElasticCloudAdapter.ACTION_SHRINK:
        click.echo('Shrinking...')
        click.echo(adapter.shrink(action_count))
            
    if next_action == ElasticCloudAdapter.ACTION_EXPAND:
        click.echo('Expanding...')
        click.echo(adapter.expand(action_count))


@cli.command()
@click.argument('driver', type=click.Choice(['gce']))
def dump_state(driver):
    adapter = adapter_choice(driver)

    adapter.update_all_states()
    states = adapter.dump_state()
    output_format = '{0: <30} {1}'
    click.echo(output_format.format('Name', 'State'))
    for name in states:
        click.echo(output_format.format(name, states[name]['status']))


@cli.command()
@click.option('--n', default=1)
@click.argument('driver', type=click.Choice(['gce']))
def shrink(n, driver):
    adapter = adapter_choice(driver)
    click.echo('Shrinking {} nodes...'.format(n))
    click.echo(adapter.shrink(n))


@cli.command()
@click.option('--n', default=1)
@click.argument('driver', type=click.Choice(['gce']))
def expand(n, driver):
    adapter = adapter_choice(driver)
    click.echo('Expanding {} nodes...'.format(n))
    click.echo(adapter.expand(n))
    
if __name__ == '__main__':
    cli()
