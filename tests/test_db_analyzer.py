import pytest
from scripts.db_analyzer import DBAnalyzer


JAVA_ENTITY_DIFF = """
+++ b/src/main/java/com/example/User.java
@@ -1,10 +1,15 @@
+import javax.persistence.*;
+
+@Entity
+@Table(name = "users")
 public class User {
+    @Column(name = "phone_number")
+    private String phoneNumber;
 }
"""

PYTHON_MODEL_DIFF = """
+++ b/app/models.py
@@ -1,5 +1,8 @@
 class User(db.Model):
+    phone = db.Column(db.String(20), nullable=False)
"""

PRISMA_DIFF = """
+++ b/prisma/schema.prisma
@@ -1,5 +1,6 @@
 model User {
+  phone String
 }
"""

NO_ENTITY_DIFF = """
+++ b/app/utils.py
@@ -1,3 +1,4 @@
+def helper():
+    pass
"""


def test_detects_jpa_entity_change():
    analyzer = DBAnalyzer()
    result = analyzer.detect_orm_changes(JAVA_ENTITY_DIFF)
    assert result["has_changes"] is True
    assert "src/main/java/com/example/User.java" in result["changed_files"]


def test_detects_sqlalchemy_model_change():
    analyzer = DBAnalyzer()
    result = analyzer.detect_orm_changes(PYTHON_MODEL_DIFF)
    assert result["has_changes"] is True


def test_detects_prisma_schema_change():
    analyzer = DBAnalyzer()
    result = analyzer.detect_orm_changes(PRISMA_DIFF)
    assert result["has_changes"] is True


def test_no_detection_for_non_entity_files():
    analyzer = DBAnalyzer()
    result = analyzer.detect_orm_changes(NO_ENTITY_DIFF)
    assert result["has_changes"] is False


def test_build_db_review_prompt_returns_string():
    analyzer = DBAnalyzer()
    changes = {"has_changes": True, "changed_files": ["User.java"], "diff_content": "diff text"}
    prompt = analyzer.build_db_review_prompt(changes)
    assert isinstance(prompt, str)
    assert len(prompt) > 0
