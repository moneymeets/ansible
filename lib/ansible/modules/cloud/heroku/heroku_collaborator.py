#!/usr/bin/python

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: heroku_collaborator
short_description: "Add or delete app collaborators on Heroku"
description:
  - Manages collaborators for Heroku apps.
author:
  - Marcel Arns <marcel.arns@moneymeets.com>
requirements:
  - heroku3
options:
  api_key:
    description:
      - Heroku API key
    required: false
    default: "no"
  apps:
    description:
      - List of Heroku App names
    required: true
    default: "no"
  suppress_invitation:
    description:
      - Suppress email invitation when creating collaborator
    required: false
    default: false
  user:
    description:
      - User ID or e-mail
    required: true
    default: "no"
  state:
    description:
      - Create or remove the heroku collaborator
    choices: ["present", "absent"]
    required: false
    default: present
notes:
  - C(HEROKU_API_KEY) and C(TF_VAR_HEROKU_API_KEY) env variable can be used instead setting c(api_key).
  - If you use c(--check), you can also pass the c(-v) flag to see affected apps in msg.
'''

EXAMPLES = '''
- heroku_collaborator:
    api_key: YOUR_API_KEY
    user: max.mustermann@example.com
    apps: heroku-example-app
    state: present

- heroku_collaborator:
    api_key: YOUR_API_KEY
    user: '{{ item.user }}'
    apps: '{{ item.apps | default(apps) }}'
    suppress_invitation: '{{ item.suppress_invitation | default(suppress_invitation) }}'
    state: '{{ item.state | default("present") }}'
  with_items:
    - { user: 'a.b@example.com' }
    - { state: 'absent', user: 'b.c@example.com', suppress_invitation: false }
    - { user: 'x.y@example.com', apps: ["heroku-example-app"] }
'''


DEPENDENCY_CHECK = True
try:
    import heroku3
except ImportError:
    DEPENDENCY_CHECK = False

from ansible.module_utils.basic import *


def add_or_delete_heroku_collaborator(module, client):

    user = module.params['user']
    state = module.params['state']
    affected_apps = []
    result_state = False

    for app in module.params['apps']:
        if app not in client.apps():
            module.fail_json(msg='App {0} does not exist'.format(app))

        heroku_app = client.apps()[app]

        heroku_collaborator_list = [collaborator.user.email for collaborator in heroku_app.collaborators()]

        if state == 'absent' and user in heroku_collaborator_list:
            if not module.check_mode:
                heroku_app.remove_collaborator(user)
            affected_apps += [app]
            result_state = True
        elif state == 'present' and user not in heroku_collaborator_list:
            if not module.check_mode:
                heroku_app.add_collaborator(user_id_or_email=user, silent=module.params['suppress_invitation'])
            affected_apps += [app]
            result_state = True

    return result_state, affected_apps


def main():

    module = AnsibleModule(
        argument_spec=dict(
            api_key=dict(default=os.getenv('HEROKU_API_KEY', os.getenv('TF_VAR_HEROKU_API_KEY')), type='str'),
            user=dict(required=True, type='str'),
            apps=dict(required=True, type='list'),
            suppress_invitation=dict(default=False, type='bool'),
            state=dict(default='present', type='str', choices=['present', 'absent']),
        ),
        supports_check_mode=True
    )

    if not DEPENDENCY_CHECK:
        module.fail_json(msg='heroku3 library required for this module (pip install heroku3)')

    client = heroku3.from_key(module.params['api_key'])

    if not client.is_authenticated:
        module.fail_json(msg='Heroku authentication failure, please check your API Key')

    # Prevent API key from appearing in debug logs
    del module.params['api_key']

    has_changed, msg = add_or_delete_heroku_collaborator(module, client)
    module.exit_json(changed=has_changed, msg=msg)


if __name__ == '__main__':
    main()
