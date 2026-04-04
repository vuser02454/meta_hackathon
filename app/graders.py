from app.models import State

class Grader:
    def score(self, state: State) -> float:
        """
        Returns a score exactly between 0.0 and 1.0. 
        In this hackathon structure, the environment normalizes cumulative_reward.
        """
        if not state:
            return 0.0
        # Ensure hard clipping between 0.0 and 1.0 as requested
        return max(0.0, min(1.0, state.cumulative_reward))
