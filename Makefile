.PHONY: test terraform-test ansible-test reporter-test lint

test: terraform-test ansible-test reporter-test

terraform-test:
	cd terraform && terraform fmt -check -recursive
	for m in modules/ahv-subnet modules/categories modules/ahv-vm; do \
	  (cd terraform/$$m && terraform init -backend=false -input=false >/dev/null && terraform validate && terraform test) || exit 1; \
	done

ansible-test:
	cd ansible && ansible-playbook --syntax-check playbooks/*.yml && ansible-lint --offline playbooks tasks
	cd ansible/tests && pytest -q

reporter-test:
	cd reporter && ruff check . && ruff format --check . && pytest -q
