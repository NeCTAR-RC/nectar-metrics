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


def test_tenant_metrics():
    for metric in naming.TENANT_METRICS:
        assert naming.from_dotted_path(f'tenant.8ffff.{metric}') == (
            f'nectar_tenant_{metric}',
            {'tenant': '8ffff'},
        )


def test_az_tenant_metrics():
    for metric in naming.TENANT_METRICS:
        assert naming.from_dotted_path(
            f'az.melbourne-qh2.tenant.8ffff.{metric}'
        ) == (
            f'nectar_az_tenant_{metric}',
            {'az': 'melbourne-qh2', 'tenant': '8ffff'},
        )


def test_host_metrics():
    for metric in naming.HOST_METRICS:
        assert naming.from_dotted_path(f'hosts.qh2_rcc_1.PT.{metric}') == (
            f'nectar_host_{metric}',
            {'host': 'qh2_rcc_1', 'home': 'PT'},
        )


def test_host_home_may_contain_a_dot():
    assert naming.from_dotted_path(
        'hosts.qh2_rcc_1.national.monash.used_vcpus'
    ) == (
        'nectar_host_used_vcpus',
        {'host': 'qh2_rcc_1', 'home': 'national.monash'},
    )


def test_site_metrics():
    for kind in ('capacity', 'usage', 'availability'):
        for resource in ('vcpu', 'memory', 'disk'):
            assert naming.from_dotted_path(
                f'sites.monash.{kind}.national.{resource}'
            ) == (
                f'nectar_site_{kind}_{resource}',
                {'site': 'monash', 'scope': 'national'},
            )


def test_idp_restores_dots():
    assert naming.from_dotted_path('users.idp_unimelb_edu_au.total') == (
        'nectar_idp_users_total',
        {'idp': 'idp.unimelb.edu.au'},
    )


def test_users_total():
    assert naming.from_dotted_path('users.total') == ('nectar_users_total', {})


def test_active_projects():
    assert naming.from_dotted_path('active.projects.compute') == (
        'nectar_active_projects',
        {'service': 'compute'},
    )


def test_unknown_paths_return_none():
    unknown = [
        # only used_vcpus exists for domain/home breakdowns
        'az.melbourne-qh2.domain.unimelb_edu_au.total_instances',
        'az.melbourne-qh2.unknown_metric',
        'tenant.8ffff.unknown_metric',
        'az.melbourne-qh2.tenant.8ffff.unknown_metric',
        'hosts.qh2_rcc_1.national.total_instances',
        'sites.monash.capacity.national.unknown_resource',
        'sites.monash.unknown_kind.national.vcpu',
        'cell.np.total_instances',
        'carbon.agents.foo.updateOperations',
    ]
    for path in unknown:
        assert naming.from_dotted_path(path) is None, path
