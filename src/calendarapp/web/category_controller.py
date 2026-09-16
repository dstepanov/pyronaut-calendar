from typing import Annotated

from jakarta.validation import Valid
from micronaut.http import HttpResponse, HttpStatus
from micronaut.http.annotation import Body, Controller, Delete, Get, Post, Status
from micronaut.scheduling import TaskExecutors
from micronaut.scheduling.annotation import ExecuteOn

from ..domain.category import Category
from ..service.category_service import CategoryService


@Controller("/api/categories")
@ExecuteOn(TaskExecutors.BLOCKING)
class CategoryController:
    def __init__(self, categories: CategoryService):
        self.categories = categories

    @Get
    def list_categories(self) -> list[Category]:
        return self.categories.all()

    @Post
    def create(self, category: Annotated[Category, Body, Valid]) -> HttpResponse[Category]:
        return HttpResponse.created(self.categories.create(category))

    @Delete("/{id}")
    @Status(HttpStatus.NO_CONTENT)
    def delete(self, id: int) -> None:
        self.categories.delete(id)
