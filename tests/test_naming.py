from nectar_metrics import naming


def test_az_metrics():
    for metric in naming.AZ_METRICS:
        assert naming.from_dotted_path(f'az.melbourne-qh2.{metric}') == (
            f'nectar_{metric}',
            {'az': 'melbourne-qh2'},
        )


def test_domain_restores_dots():
    assert naming.from_dotted_path(
        'az.melbourne-qh2.domain.unimelb_edu_au.used_vcpus'
    ) == (
        'nectar_domain_used_vcpus',
        {'az': 'melbourne-qh2', 'domain': 'unimelb.edu.au'},
    )


def test_allocation_home():
    assert naming.from_dotted_path(
        'az.monash-01.allocation_home.monash.used_vcpus'
    ) == (
        'nectar_allocation_home_used_vcpus',
        {'az': 'monash-01', 'home': 'monash'},
    )


def test_users_total():
    assert naming.from_dotted_path('users.total') == ('nectar_users_total', {})


def test_active_projects():
    assert naming.from_dotted_path('active.projects.compute') == (
        'nectar_active_projects',
        {'service': 'compute'},
    )


def test_unmigrated_paths_return_none():
    unmigrated = [
        'tenant.8ffff.total_instances',
        'az.melbourne-qh2.tenant.8ffff.used_vcpus',
        'users.idp_unimelb_edu_au.total',
        'hosts.qh2_rcc_1.national.used_vcpus',
        'sites.monash.capacity.national.vcpu',
        # only used_vcpus exists for domain/home breakdowns
        'az.melbourne-qh2.domain.unimelb_edu_au.total_instances',
        'az.melbourne-qh2.unknown_metric',
        'cell.np.total_instances',
        'carbon.agents.foo.updateOperations',
    ]
    for path in unmigrated:
        assert naming.from_dotted_path(path) is None, path
