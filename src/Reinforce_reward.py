import os
import json

from time import time
from copy import deepcopy
from stable_baselines3 import DQN, A2C, PPO

from Dataset import Dataset
from Reinforce import Reinforce

from CourseRecEnv import EvaluateCallback, CourseRecEnv
from CourseRecEnv_reward import EvaluateCallback_reward, CourseRecEnv_reward

  

 
class Reinforce_reward(Reinforce):
    def __init__(
        self, dataset, model, k, threshold, run,type_,  total_steps=1000, eval_freq=100
    ):
        # Appel au constructeur de la classe mère avec une classe d'environnement spécifique
        super().__init__(dataset, model, k, threshold, run, type_ , total_steps, eval_freq,
                         env_class=CourseRecEnv_reward, callback_class=EvaluateCallback_reward)

    def get_model(self):
        """Sets the model to be used for the recommendation. The model is from stable-baselines3 and is chosen based on the model_name attribute."""
        if self.model_name == "dqn":
            self.model = DQN(env=self.train_env, verbose=0, policy="MlpPolicy", device="auto")
        elif self.model_name == "a2c":
            self.model = A2C(
                env=self.train_env, verbose=0, policy="MlpPolicy", device="auto"
            )
        elif self.model_name == "ppo":
            self.model = PPO(env=self.train_env, verbose=0, policy="MlpPolicy", device="auto")

    def update_learner_profile(self, learner, course):
        """Updates the learner's profile with the skills and levels of the course.

        Args:
            learner (list): list of skills and mastery level of the learner
            course (list): list of required (resp. provided) skills and mastery level of the course
        """
        # Update the learner profile with the skills and levels provided by the course (course [1] is the list of skills and levels provided by the course)
        for cskill, clevel in course[1]:
            found = False
            i = 0
            while not found and i < len(learner):
                lskill, llevel = learner[i]
                if cskill == lskill:
                    learner[i] = (lskill, max(llevel, clevel))
                    found = True
                i += 1
            if not found:
                learner.append((cskill, clevel))

    def reinforce_recommendation(self):
        """Train and evaluates the reinforcement learning model to make recommendations for every learner in the dataset. The results are saved in a json file."""
        results = dict()

        avg_l_attrac = self.dataset.get_avg_learner_attractiveness()

        print(f"-----------------------------------------------------------------")
        print(f"The average attractiveness of the learners is {avg_l_attrac:.2f}")

        results["original_attractiveness"] = avg_l_attrac

        avg_app_j = self.dataset.get_avg_applicable_jobs(self.threshold)
        print(f"The average nb of applicable jobs per learner is {avg_app_j:.2f}")

        results["original_applicable_jobs"] = avg_app_j

        original_avg_matching=self.dataset.get_average_matching_job_learners()

        print(f"The matching between learners and jobs is {original_avg_matching}")

        results["original_avg_matching"] = original_avg_matching

        # Train the model
        self.model.learn(total_timesteps=self.total_steps, callback=self.eval_callback)

        # Evaluate the model
        time_start = time()
        recommendations = dict()
        for i, learner in enumerate(self.dataset.learners):
            job_wanted=self.dataset.learners_wanted[i]
            self.eval_env.reset(learner=learner, job_wanted=job_wanted)
            done = False
            index = self.dataset.learners_index[i]
            recommendation_sequence = []
            while not done:
                recherche_job =self.dataset.learners_wanted[i]

                obs = self.eval_env._get_obs()
                action, _state = self.model.predict(obs, deterministic=True)
                obs, reward, done, _, info = self.eval_env.step(action)
                if reward != -1:
                    recommendation_sequence.append(action.item())
            for course in recommendation_sequence:
                self.update_learner_profile(learner, self.dataset.courses[course])

            recommendations[index] = [
                self.dataset.courses_index[course_id]
                for course_id in recommendation_sequence
            ]

        time_end = time()
        avg_recommendation_time = (time_end - time_start) / len(self.dataset.learners)
        print(f"-----------------------------------------------------------------")

        print(f"Average Recommendation Time: {avg_recommendation_time:.2f} seconds")

        results["avg_recommendation_time"] = avg_recommendation_time
        avg_l_attrac = self.dataset.get_avg_learner_attractiveness()

        print(f"The new average attractiveness of the learners is {avg_l_attrac:.2f}")

        results["new_attractiveness"] = avg_l_attrac

        avg_app_j = self.dataset.get_avg_applicable_jobs(self.threshold)
        print(f"The new average nb of applicable jobs per learner is {avg_app_j:.2f}")

        new_avg_matching=self.dataset.get_average_matching_job_learners()
        print(f"The new matching between learners and jobs is {new_avg_matching}")

        print(f"-----------------------------------------------------------------")

        results["new_applicable_jobs"] = avg_app_j

        results["new_avg_matching"] = new_avg_matching


        results["recommendations"] = recommendations
        
        json.dump(
            results,
            open(
                os.path.join(
                    self.dataset.config["results_path"],
                    self.final_results_filename,
                ),
                "w",
            ),
            indent=4,
        )