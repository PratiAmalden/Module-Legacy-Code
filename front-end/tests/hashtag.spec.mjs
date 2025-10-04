import { test, expect } from "@playwright/test";

test.describe("hashtag view", () => {
    test("should only make one fetch request when navigating to a hashtag", async ({ page }) => {
        let fetchCount = 0;
        page.on("request", (request) => {
        if (
            request.url().includes(":3000/hashtag/do") &&
            request.resourceType() === "fetch"
        ) {
            fetchCount++;
        }
        });
        // When I navigate to the hashtag
        await page.goto("/#/hashtag/do");
        // And I wait a reasonable time for any additional requests
        await page.waitForTimeout(200);

        // Then the number of fetch requests should be 1
        expect(fetchCount).toEqual(1);
        });
});